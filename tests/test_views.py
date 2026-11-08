from base64 import b64encode
from decimal import Decimal
from html import unescape
from re import findall, search

import django
import pytest
from redsys import transactions
from redsys.clients import RedirectClient

from redsys_gateway import signals

from .conftest import decoded, signed


def _hostile(json_text):
    return {'Ds_MerchantParameters': b64encode(json_text.encode()).decode(), 'Ds_Signature': 'x'}


def _form(response):
    html = response.content.decode()
    action = unescape(search(r'action="([^"]+)"', html).group(1))
    fields = {name: unescape(value) for name, value in findall(r'name="([^"]+)" value="([^"]*)"', html)}
    return action, fields


@pytest.fixture
def received():
    events = []

    def receiver(signal, sender, **kwargs):
        events.append((signal, kwargs))

    names = ['request_created', 'notification_received', 'notification_authorized', 'notification_denied']
    for name in [*names, 'notification_invalid']:
        getattr(signals, name).connect(receiver, weak=False)
    yield events
    for name in [*names, 'notification_invalid']:
        getattr(signals, name).disconnect(receiver)


# == Payment views ==
def test_payment_view_renders_the_signed_form(client, received):
    response = client.get('/pay/1234abcd/')
    assert response.status_code == 200
    assert 'no-store' in response['Cache-Control']
    action, fields = _form(response)
    assert action == RedirectClient.TEST_ENDPOINT
    assert set(fields) == {'Ds_SignatureVersion', 'Ds_MerchantParameters', 'Ds_Signature'}
    parameters = decoded(fields)
    assert parameters['Ds_Merchant_Order'] == '1234abcd'
    assert parameters['Ds_Merchant_Amount'] == 1056
    assert parameters['Ds_Merchant_TransactionType'] == transactions.AUTHORIZATION
    assert parameters['Ds_Merchant_MerchantData'] == 'cart=7'
    assert parameters['Ds_Merchant_MerchantURL'] == 'http://testserver/redsys/notification/'
    assert parameters['Ds_Merchant_UrlOK'] == 'http://testserver/redsys/ok/'
    assert parameters['Ds_Merchant_UrlKO'] == 'http://testserver/redsys/ko/'
    [(signal, kwargs)] = received
    assert signal is signals.request_created
    assert kwargs['fields']['order'] == '1234abcd'
    assert kwargs['redsys_request'].to_dict() == fields


def test_view_fields_win_and_transaction_type_is_the_view_s(client):
    parameters = decoded(_form(client.get('/preauthorize/'))[1])
    assert parameters['Ds_Merchant_TransactionType'] == transactions.PREAUTHORIZATION
    assert parameters['Ds_Merchant_UrlOK'] == 'https://shop.example/thanks'


def test_view_without_fields_raises():
    from django.test import Client

    with pytest.raises(NotImplementedError):
        Client(raise_request_exception=True).get('/missing/')


def test_invalid_fields_raise_before_signing(client, received, settings):
    settings.REDSYS_CLIENT = {**settings.REDSYS_CLIENT, 'currency': 1}
    with pytest.raises(ValueError):
        client.get('/pay/1234abcd/')
    assert received == []


def test_payment_view_also_answers_post(client):
    assert decoded(_form(client.post('/pay/1234abcd/'))[1])['Ds_Merchant_Order'] == '1234abcd'


def test_form_view_shows_the_form_on_get_and_on_errors(client, received):
    assert 'name="amount"' in client.get('/pay-form/').content.decode()
    response = client.post('/pay-form/', {'amount': 'ten'})
    assert response.status_code == 200
    assert response.context['form'].errors
    assert received == []


def test_form_view_signs_with_the_cleaned_data(client):
    parameters = decoded(_form(client.post('/pay-form/', {'amount': '2.49'}))[1])
    assert (parameters['Ds_Merchant_Order'], parameters['Ds_Merchant_Amount']) == ('5678efgh', 249)


@pytest.mark.skipif(django.VERSION < (6, 0), reason='Django 6.0 added the CSP middleware')
def test_redirect_template_carries_the_csp_nonce(client, settings):
    from django.utils.csp import CSP

    settings.MIDDLEWARE = ['django.middleware.csp.ContentSecurityPolicyMiddleware']
    settings.SECURE_CSP = {'script-src': [CSP.NONCE]}
    settings.TEMPLATES = [
        {
            **settings.TEMPLATES[0],
            'OPTIONS': {'context_processors': ['django.template.context_processors.csp']},
        }
    ]
    response = client.get('/pay/1234abcd/')
    nonce = search(r'<script nonce="([^"]+)">', response.content.decode()).group(1)
    assert f"'nonce-{nonce}'" in response['Content-Security-Policy']


# == Notification ==
def test_authorized_notification(client, received, notification):
    response = client.post('/redsys/notification/', signed(notification))
    assert response.status_code == 200
    signal_names = [signal for signal, _ in received]
    assert signal_names == [signals.notification_received, signals.notification_authorized]
    redsys_response = received[0][1]['response']
    assert (redsys_response.order, redsys_response.amount, redsys_response.merchant_data) == (
        '1234abcd',
        Decimal('10.56'),
        'cart=7',
    )


@pytest.mark.parametrize('version', ['HMAC_SHA256_V1', 'HMAC_SHA512_V1'])
def test_notification_in_other_signature_versions(client, received, notification, version):
    assert client.post('/redsys/notification/', signed(notification, version=version)).status_code == 200


def test_denied_notification(client, received, notification):
    notification['Ds_Response'] = '0190'
    assert client.post('/redsys/notification/', signed(notification)).status_code == 200
    assert [signal for signal, _ in received] == [signals.notification_received, signals.notification_denied]


@pytest.mark.parametrize(
    'tamper',
    [
        lambda fields: {**fields, 'Ds_Signature': 'x' + fields['Ds_Signature'][1:]},
        lambda fields: {k: v for k, v in fields.items() if k != 'Ds_Signature'},
        lambda fields: {k: v for k, v in fields.items() if k != 'Ds_MerchantParameters'},
        lambda fields: {**fields, 'Ds_MerchantParameters': 'not base64 json'},
        lambda fields: {**fields, 'Ds_SignatureVersion': 'HMAC_MD5'},
        lambda fields: {},
        lambda fields: _hostile('{"Ds_Amount": "1E99999999", "Ds_Order": "1"}'),
        lambda fields: _hostile('[' * 100000 + ']' * 100000),
        lambda fields: _hostile('"just a string"'),
    ],
)
def test_invalid_notification_is_rejected(client, received, notification, tamper):
    response = client.post('/redsys/notification/', tamper(signed(notification)))
    assert response.status_code == 400
    [(signal, kwargs)] = received
    assert signal is signals.notification_invalid
    assert isinstance(kwargs['error'], Exception)


def test_notification_signed_with_another_key_is_rejected(client, received, notification):
    fields = signed(notification, secret_key='Mk9m98IfEblmPfrpsawt7BmxObt98Jev')
    assert client.post('/redsys/notification/', fields).status_code == 400


def test_notification_needs_no_csrf_token_and_only_takes_post(notification):
    from django.test import Client

    csrf_client = Client(enforce_csrf_checks=True)
    assert csrf_client.post('/redsys/notification/', signed(notification)).status_code == 200
    assert csrf_client.get('/redsys/notification/').status_code == 405


# == OK and KO pages ==
@pytest.mark.parametrize('page', ['ok', 'ko'])
def test_result_page_shows_the_verified_response(client, notification, page):
    response = client.get(f'/redsys/{page}/', signed(notification))
    assert response.status_code == 200
    assert response.context['redsys_response'].order == '1234abcd'
    assert 'Order 1234abcd.' in response.content.decode()


@pytest.mark.parametrize(
    'query',
    [{}, {'Ds_MerchantParameters': 'x', 'Ds_Signature': 'y'}, _hostile('{"Ds_Amount": "1E99999999", "Ds_Order": "1"}')],
)
def test_result_page_without_a_valid_response(client, query):
    response = client.get('/redsys/ok/', query)
    assert response.status_code == 200
    assert response.context['redsys_response'] is None


def test_result_page_ignores_a_tampered_response(client, notification):
    fields = signed(notification)
    fields['Ds_Signature'] = 'x' + fields['Ds_Signature'][1:]
    assert client.get('/redsys/ko/', fields).context['redsys_response'] is None
