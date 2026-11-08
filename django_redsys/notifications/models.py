from hashlib import sha256
from ipaddress import ip_address

from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _address(value):
    try:
        return str(ip_address(value))
    except ValueError:
        return None


class NotificationManager(models.Manager):
    def register(self, merchant_parameters, response, environment='', remote_addr=None):
        """Records a verified notification; ``True`` for the first arrival of its payload, ``False`` for a repeat."""

        def text(name):
            # Values are signed by RedSys but their lengths are not the database's to trust.
            return (getattr(response, name) or '')[: self.model._meta.get_field(name).max_length]

        now = timezone.now()
        notification, created = self.get_or_create(
            digest=sha256(merchant_parameters.encode()).hexdigest(),
            defaults={
                'order': text('order'),
                'response_code': response.response_code,
                'authorized': response.is_authorized(),
                'amount': response.amount,
                'currency': response.currency,
                'transaction_type': text('transaction_type'),
                'authorization_code': text('authorization_code'),
                'merchant_code': text('merchant_code'),
                'terminal': text('terminal'),
                'environment': environment or '',
                'secure_payment': text('secure_payment'),
                'processed_pay_method': text('processed_pay_method'),
                'error_code': text('error_code'),
                'redsys_date': (response.date or '')[:16],
                'redsys_hour': (response.hour or '')[:16],
                'remote_addr': _address(remote_addr or ''),
                'received_at': now,
                'last_received_at': now,
            },
        )
        if not created:
            self.filter(pk=notification.pk).update(count=F('count') + 1, last_received_at=now)
        return created


class Notification(models.Model):
    digest = models.CharField(_('payload digest'), max_length=64, unique=True)
    order = models.CharField(_('order'), max_length=32, db_index=True)
    response_code = models.IntegerField(_('response code'), null=True, blank=True)
    authorized = models.BooleanField(_('authorized'))
    amount = models.DecimalField(_('amount'), max_digits=15, decimal_places=3, null=True, blank=True)
    currency = models.IntegerField(_('currency'), null=True, blank=True)
    transaction_type = models.CharField(_('transaction type'), max_length=8, blank=True)
    authorization_code = models.CharField(_('authorization code'), max_length=16, blank=True)
    merchant_code = models.CharField(_('merchant code'), max_length=16, blank=True)
    terminal = models.CharField(_('terminal'), max_length=8, blank=True)
    environment = models.CharField(_('environment'), max_length=8, blank=True)
    secure_payment = models.CharField(_('secure payment'), max_length=4, blank=True)
    processed_pay_method = models.CharField(_('processed payment method'), max_length=8, blank=True)
    error_code = models.CharField(_('error code'), max_length=16, blank=True)
    redsys_date = models.CharField(_('RedSys date'), max_length=16, blank=True)
    redsys_hour = models.CharField(_('RedSys hour'), max_length=16, blank=True)
    remote_addr = models.GenericIPAddressField(_('sender address'), null=True, blank=True)
    received_at = models.DateTimeField(_('received at'), db_index=True)
    last_received_at = models.DateTimeField(_('last received at'))
    count = models.PositiveIntegerField(_('arrivals'), default=1)

    objects = NotificationManager()

    class Meta:
        ordering = ['-received_at']
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')

    def __str__(self):
        return f'{self.order} {self.response_code}'
