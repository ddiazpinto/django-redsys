from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View
from redsys import transactions

from .client import get_client
from .signals import (
    notification_authorized,
    notification_denied,
    notification_invalid,
    notification_received,
    request_created,
)


class RedsysPaymentMixin:
    """Signs a redirect-connection operation and renders the form that posts it to RedSys."""

    transaction_type = transactions.AUTHORIZATION
    redirect_template_name = 'django_redsys/redirect.html'

    def get_redsys_fields(self):
        raise NotImplementedError('get_redsys_fields() must return the operation fields, order and amount included.')

    def get_redsys_request(self):
        fields = {
            'merchant_url': self.request.build_absolute_uri(reverse('django_redsys:notification')),
            'url_ok': self.request.build_absolute_uri(reverse('django_redsys:ok')),
            'url_ko': self.request.build_absolute_uri(reverse('django_redsys:ko')),
            **self.get_redsys_fields(),
        }
        redsys_request = get_client().request(self.transaction_type, **fields)
        request_created.send(sender=type(self), request=self.request, redsys_request=redsys_request, fields=fields)
        return redsys_request

    def redirect_to_redsys(self):
        redsys_request = self.get_redsys_request()
        context = {'endpoint': redsys_request.endpoint, 'fields': redsys_request.to_dict()}
        response = render(self.request, self.redirect_template_name, context)
        # A cached form would resubmit a used order number (SIS0051).
        add_never_cache_headers(response)
        return response


class RedsysPaymentView(RedsysPaymentMixin, View):
    def get(self, request, *args, **kwargs):
        return self.redirect_to_redsys()

    def post(self, request, *args, **kwargs):
        return self.redirect_to_redsys()


class RedsysPaymentFormView(RedsysPaymentMixin, FormView):
    def form_valid(self, form):
        self.form = form
        return self.redirect_to_redsys()


@method_decorator(csrf_exempt, name='dispatch')
class NotificationView(View):
    """Receives the server-to-server notification RedSys posts to ``merchant_url``."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        client = get_client()
        try:
            response = client.parse_response(request.POST.dict())
        # The payload is untrusted input: any failure to parse or verify it makes the notification invalid.
        except Exception as error:
            notification_invalid.send(sender=type(self), request=request, error=error)
            raise SuspiciousOperation('RedSys notification failed verification.') from error
        notification_received.send(sender=type(self), request=request, response=response)
        outcome = notification_authorized if response.is_authorized() else notification_denied
        outcome.send(sender=type(self), request=request, response=response)
        return HttpResponse()


class ResultView(TemplateView):
    """The ``url_ok`` / ``url_ko`` page; ``redsys_response`` is the verified result RedSys appends, or ``None``."""

    def get_redsys_response(self):
        payload = self.request.GET.dict()
        if not payload:
            return None
        client = get_client()
        try:
            return client.parse_response(payload)
        except Exception:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['redsys_response'] = self.get_redsys_response()
        return context
