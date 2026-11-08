from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.management import CommandError, call_command
from django.test import Client, override_settings
from django.utils import timezone

from django_redsys import signals
from django_redsys.notifications.admin import NotificationAdmin
from django_redsys.notifications.models import Notification

from .conftest import signed

URL = '/redsys/notification/'


@pytest.fixture
def received():
    events = []

    def receiver(signal, sender, **kwargs):
        events.append(signal)

    names = ['notification_received', 'notification_authorized', 'notification_denied', 'notification_repeated']
    for name in names:
        getattr(signals, name).connect(receiver, weak=False)
    yield events
    for name in names:
        getattr(signals, name).disconnect(receiver)


def test_first_arrival_is_recorded_and_processed(client, received, notification):
    assert client.post(URL, signed(notification), REMOTE_ADDR='192.0.2.10').status_code == 200
    assert received == [signals.notification_received, signals.notification_authorized]
    record = Notification.objects.get()
    assert (record.order, record.response_code, record.authorized, record.amount, record.currency) == (
        '1234abcd',
        0,
        True,
        Decimal('10.56'),
        978,
    )
    assert (record.transaction_type, record.merchant_code, record.terminal) == ('0', '999008881', '1')
    assert (record.remote_addr, record.count, str(record)) == ('192.0.2.10', 1, '1234abcd 0')
    assert (record.environment, record.secure_payment, record.processed_pay_method) == ('TEST', '1', '1')
    assert (record.error_code, record.redsys_date, record.redsys_hour) == ('', '08/11/2026', '12:30')


def test_a_repeat_is_counted_and_only_sends_notification_repeated(client, received, notification):
    fields = signed(notification)
    client.post(URL, fields)
    received.clear()
    assert client.post(URL, fields).status_code == 200
    assert received == [signals.notification_repeated]
    record = Notification.objects.get()
    assert record.count == 2
    assert record.last_received_at > record.received_at


def test_another_result_for_the_same_order_is_new(client, received, notification):
    client.post(URL, signed(notification))
    notification.update({'Ds_Response': '0190', 'Ds_ErrorCode': 'SIS0093'})
    client.post(URL, signed(notification))
    assert signals.notification_denied in received
    denied = Notification.objects.get(authorized=False)
    assert (denied.response_code, denied.error_code) == (190, 'SIS0093')
    assert Notification.objects.filter(authorized=True).exists()


def test_a_failing_receiver_leaves_nothing_recorded(received, notification):
    def fail(**kwargs):
        raise RuntimeError('receiver failed')

    signals.notification_authorized.connect(fail, weak=False)
    try:
        response = Client(raise_request_exception=False).post(URL, signed(notification))
    finally:
        signals.notification_authorized.disconnect(fail)
    assert response.status_code == 500
    assert not Notification.objects.exists()
    received.clear()
    Client().post(URL, signed(notification))
    assert received == [signals.notification_received, signals.notification_authorized]


def test_invalid_notifications_are_not_recorded(client, notification):
    fields = signed(notification)
    fields['Ds_Signature'] = 'x' + fields['Ds_Signature'][1:]
    assert client.post(URL, fields).status_code == 400
    assert not Notification.objects.exists()


def test_long_values_and_odd_addresses_fit(client, notification):
    notification['Ds_AuthorisationCode'] = 'A' * 40
    client.post(URL, signed(notification), REMOTE_ADDR='not an address')
    record = Notification.objects.get()
    assert (record.authorization_code, record.remote_addr) == ('A' * 16, None)


def test_without_the_app_nothing_is_recorded_and_repeats_are_processed(client, received, notification, settings):
    apps = [app for app in settings.INSTALLED_APPS if app != 'django_redsys.notifications']
    fields = signed(notification)
    with override_settings(INSTALLED_APPS=apps):
        client.post(URL, fields)
        client.post(URL, fields)
    assert received.count(signals.notification_authorized) == 2
    assert not Notification.objects.exists()


def test_purge_deletes_by_first_arrival(client, notification):
    client.post(URL, signed(notification))
    Notification.objects.update(received_at=timezone.now() - timedelta(days=40))
    call_command('purge_redsys_notifications', '--older-than', '60')
    assert Notification.objects.exists()
    call_command('purge_redsys_notifications', '--older-than', '30')
    assert not Notification.objects.exists()
    with pytest.raises(CommandError):
        call_command('purge_redsys_notifications', '--older-than', '-1')


def test_admin_is_read_only():
    model_admin = NotificationAdmin(Notification, admin.site)
    assert isinstance(admin.site._registry[Notification], NotificationAdmin)
    assert not model_admin.has_add_permission(None)
    assert not model_admin.has_change_permission(None)
