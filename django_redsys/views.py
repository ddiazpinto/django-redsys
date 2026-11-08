from contextlib import nullcontext
from ipaddress import ip_address

from django.apps import apps
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import router, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View
from redsys import transactions
from redsys.clients import MERCHANT_PARAMETERS

from .client import get_client
from .conf import notification_networks
from .signals import (
    notification_authorized,
    notification_denied,
    notification_invalid,
    notification_received,
    notification_repeated,
    request_created,
)

NOTIFICATIONS_APP = 'django_redsys.notifications'


class RedsysClientMixin:
    def get_redsys_client(self):
        """The python-redsys client of this view; ``get_client()`` unless a subclass picks another account."""
        return get_client()


class RedsysPaymentMixin(RedsysClientMixin):
    """Signs a redirect-connection operation and renders the form that posts it to RedSys."""

    transaction_type = transactions.AUTHORIZATION
    redirect_template_name = 'django_redsys/redirect.html'

    def get_redsys_fields(self):
        raise NotImplementedError('get_redsys_fields() must return the operation fields, or None for no order.')

    def get_redsys_request(self):
        operation_fields = self.get_redsys_fields()
        if not operation_fields:
            raise Http404('No order to pay.')
        fields = {
            'merchant_url': self.request.build_absolute_uri(reverse('django_redsys:notification')),
            'url_ok': self.request.build_absolute_uri(reverse('django_redsys:ok')),
            'url_ko': self.request.build_absolute_uri(reverse('django_redsys:ko')),
            **operation_fields,
        }
        redsys_request = self.get_redsys_client().request(self.transaction_type, **fields)
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
class NotificationView(RedsysClientMixin, View):
    """Receives the server-to-server notification RedSys posts to ``merchant_url``."""

    http_method_names = ['post']

    def is_allowed_sender(self):
        networks = notification_networks()
        if networks is None:
            return True
        try:
            address = ip_address(self.request.META.get('REMOTE_ADDR', ''))
        except ValueError:
            return False
        return any(address in network for network in networks)

    def post(self, request, *args, **kwargs):
        if not self.is_allowed_sender():
            error = PermissionDenied('RedSys notification from an address outside REDSYS_NOTIFICATION_IPS.')
            notification_invalid.send(sender=type(self), request=request, error=error)
            raise error
        client = self.get_redsys_client()
        try:
            response = client.parse_response(request.POST.dict())
        # The payload is untrusted input: any failure to parse or verify it makes the notification invalid.
        except Exception as error:
            notification_invalid.send(sender=type(self), request=request, error=error)
            raise SuspiciousOperation('RedSys notification failed verification.') from error
        # Recording and receivers commit together: a receiver that fails leaves the notification unrecorded.
        with self.processing():
            if not self.register_notification(response, client):
                notification_repeated.send(sender=type(self), request=request, response=response)
                return HttpResponse()
            notification_received.send(sender=type(self), request=request, response=response)
            outcome = notification_authorized if response.is_authorized() else notification_denied
            outcome.send(sender=type(self), request=request, response=response)
        return HttpResponse()

    def recording(self):
        return apps.is_installed(NOTIFICATIONS_APP)

    def processing(self):
        if not self.recording():
            return nullcontext()
        from .notifications.models import Notification

        return transaction.atomic(using=router.db_for_write(Notification))

    def register_notification(self, response, client):
        """Whether the notification is new: always without ``django_redsys.notifications``, else per its record."""
        if not self.recording():
            return True
        from .notifications.models import Notification

        return Notification.objects.register(
            self.request.POST.get(MERCHANT_PARAMETERS, ''),
            response,
            environment=client.environment,
            remote_addr=self.request.META.get('REMOTE_ADDR'),
        )


class ResultView(RedsysClientMixin, TemplateView):
    """The ``url_ok`` / ``url_ko`` page: 404 unless RedSys appended a verified result with the expected outcome."""

    authorized = True

    def get_redsys_response(self):
        payload = self.request.GET.dict()
        if not payload:
            return None
        client = self.get_redsys_client()
        try:
            return client.parse_response(payload)
        except Exception:
            return None

    def get(self, request, *args, **kwargs):
        self.redsys_response = self.get_redsys_response()
        if self.redsys_response is None or self.redsys_response.is_authorized() != self.authorized:
            raise Http404('No RedSys result to show.')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['redsys_response'] = self.redsys_response
        return context
