from django.utils.translation import ugettext as _
from django.views.generic.edit import FormView, View
from django.views.generic.base import TemplateView
from django.utils.module_loading import import_string
from django.conf import settings
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.exceptions import SuspiciousOperation
from redsys.client import RedirectClient, SIGNATURE, MERCHANT_PARAMETERS, SIGNATURE_VERSION
from .signals import (
    pre_transaction, post_transaction, transaction_accepted,
    transaction_rejected, invalid_response, suspicious_response
)
from .forms import GatewayForm


class RedsysRedirectMixin(object):

    def get_order_object(self, request, *args, **kwargs):
        return None

    def get_order(self, request, *args, **kwargs):
        raise NotImplementedError

    def get_amount(self, request, *args, **kwargs):
        raise NotImplementedError

    def get_merchant_data(self, request, *args, **kwargs):
        return ""

    def get_request_parameters(self, request, *args, **kwargs):
        return {}

    def get_redirection_template_name(self):
        return 'redsys_gateway/redirect.html'

    def process(self, request, *args, **kwargs):
        client = RedirectClient(settings.REDSYS_SECRET_KEY, settings.REDSYS_SANDBOX)
        transaction_request = client.create_request()
        # Set default data and merchant data provided in settings
        transaction_request.merchant_code = settings.REDSYS_MERCHANT_CODE
        transaction_request.merchant_name = settings.REDSYS_MERCHANT_NAME
        transaction_request.titular = settings.REDSYS_TITULAR
        transaction_request.terminal = settings.REDSYS_TERMINAL
        transaction_request.product_description = settings.REDSYS_PRODUCT_DESCRIPTION
        transaction_request.merchant_url = request.build_absolute_uri(reverse("redsys_gateway:response"))
        transaction_request.url_ok = request.build_absolute_uri(reverse("redsys_gateway:accepted"))
        transaction_request.url_ko = request.build_absolute_uri(reverse("redsys_gateway:rejected"))
        transaction_request.currency = settings.REDSYS_CURRENCY
        transaction_request.transaction_type = settings.REDSYS_TRANSACTIONTYPE
        # Set custom data
        order_object = self.get_order_object(request, *args, **kwargs)
        transaction_request.order = self.get_order(request, *args, **kwargs)
        transaction_request.amount = self.get_amount(request, *args, **kwargs)
        transaction_request.merchant_data = self.get_merchant_data(request, *args, **kwargs)
        request_parameters = self.get_request_parameters(request, *args, **kwargs)
        for key, value in request_parameters.items():
            setattr(transaction_request, key, value)
        args = client.prepare_request(transaction_request)
        args.update({'endpoint': client.endpoint})
        pre_transaction.send(sender=self, request=request, order_object=order_object, transaction_request=transaction_request)
        return HttpResponse(render(request, self.get_redirection_template_name(), args))


class RedsysRedirectTemplateView(RedsysRedirectMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        return self.process(request, *args, **kwargs)


class RedsysRedirectFormView(RedsysRedirectMixin, FormView):

    def form_valid(self, form):
        return self.process(self.request)


@csrf_exempt
def response_view(request):
    form = GatewayForm(request.POST)
    if form.is_valid():
        client = RedirectClient(settings.REDSYS_SECRET_KEY, settings.REDSYS_SANDBOX)
        try:
            transaction_response = client.create_response(
                form.cleaned_data[SIGNATURE],
                form.cleaned_data[MERCHANT_PARAMETERS],
                form.cleaned_data[SIGNATURE_VERSION]
            )
        except ValueError:
            suspicious_response.send(sender=None, request=request, form=form)
            raise SuspiciousOperation(_("It is impossible to create the response object from request data."))
        post_transaction.send(sender=None, request=request, transaction_response=transaction_response)
        if transaction_response.is_authorized():
            transaction_accepted.send(sender=None, request=request, transaction_response=transaction_response)
        else:
            transaction_rejected.send(sender=None, request=request, transaction_response=transaction_response)
    else:
        invalid_response.send(sender=None, request=request, form=form)
        raise SuspiciousOperation(_("Response data do not meet the necessary format."))
    return HttpResponse()


def redirect_view(request):
    return import_string(settings.REDSYS_REDIRECT_VIEW).as_view()(request)


def accepted_view(request):
    view = getattr(settings, 'REDSYS_TRANSACTION_ACCEPTED_VIEW', None)
    if view:
        return import_string(view).as_view()(request)
    else:
        return TemplateView.as_view(template_name='redsys_gateway/accepted.html')(request)


def rejected_view(request):
    view = getattr(settings, 'REDSYS_TRANSACTION_REJECTED_VIEW', None)
    if view:
        return import_string(view).as_view()(request)
    else:
        return TemplateView.as_view(template_name='redsys_gateway/rejected.html')(request)
