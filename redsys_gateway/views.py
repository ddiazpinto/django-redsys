from django.views.generic.edit import FormView
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.core.exceptions import SuspiciousOperation
from redsys.client import RedirectClient, SIGNATURE, MERCHANT_PARAMETERS, SIGNATURE_VERSION

from .signals import pre_transaction, post_transaction, transaction_accepted, transaction_rejected
from .forms import GatewayForm


class RedirectView(FormView):

    amount = None
    order = None

    def get_order(self, form):
        return self.order

    def get_amount(self, form):
        return self.amount

    def get_merchant_data(self, form):
        return ''

    def set_request_parameters(self, request, form):
        return request

    def form_valid(self, form):
        url_base = "{0}://{1}".format(self.request.scheme, self.request.get_host())
        client = RedirectClient(settings.REDSYS_SECRET_KEY, settings.REDSYS_SANDBOX)
        request = client.create_request()
        request.merchant_code = settings.REDSYS_MERCHANT_CODE
        request.merchant_name = settings.REDSYS_MERCHANT_NAME
        request.titular = settings.REDSYS_TITULAR
        request.terminal = settings.REDSYS_TERMINAL
        request.product_description = settings.REDSYS_PRODUCT_DESCRIPTION
        request.merchant_url = url_base + reverse("redsys_gateway-response")
        request.url_ok = url_base + reverse("redsys_gateway-transaction-accepted")
        request.url_ko = url_base + reverse("redsys_gateway-transaction-rejected")
        request.currency = settings.REDSYS_CURRENCY
        request.transaction_type = settings.REDSYS_TRANSACTIONTYPE
        request.order = self.get_order(form)
        request.amount = self.get_amount(form)
        request.merchant_data = self.get_merchant_data(form)
        request = self.set_request_parameters(request, form)
        args = client.prepare_request(request)
        args.update({
            'endpoint': client.endpoint
        })
        pre_transaction.send(sender=self, request=request, form=form)
        self.template_name = 'redsys_gateway/redirect.html'
        return self.render_to_response(self.get_context_data(**args))


@csrf_exempt
def response_view(request):
    form = GatewayForm(request.POST)
    if form.is_valid():
        client = RedirectClient(settings.REDSYS_SECRET_KEY, settings.REDSYS_SANDBOX)
        response = client.create_response(form.cleaned_data[SIGNATURE],
                                          form.cleaned_data[MERCHANT_PARAMETERS],
                                          form.cleaned_data[SIGNATURE_VERSION])
        post_transaction.send(sender=None, response=response)
        if response.is_authorized():
            transaction_accepted.send(sender=None, response=response)
        else:
            transaction_rejected.send(sender=None, response=response)
    else:
        raise SuspiciousOperation()
    return HttpResponse()
