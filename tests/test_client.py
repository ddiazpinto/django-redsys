from base64 import urlsafe_b64encode

import pytest
from django.core.exceptions import ImproperlyConfigured
from redsys import environments
from redsys.clients import DirectClient, RedirectClient

from django_redsys.client import get_client


def test_builds_a_redirect_client_from_the_setting():
    client = get_client()
    assert isinstance(client, RedirectClient)
    assert (client.merchant_code, client.terminal, client.environment) == ('999008881', 1, environments.TEST)


def test_builds_another_client_class():
    assert isinstance(get_client(DirectClient), DirectClient)


def test_api_key_goes_through_from_api_key_with_the_other_options(settings):
    payload = urlsafe_b64encode(b'999008881_2_secret').decode().rstrip('=')
    settings.REDSYS_CLIENT = {'api_key': f'{environments.TEST}_{payload}', 'currency': 840}
    client = get_client()
    assert (client.merchant_code, client.terminal, client.environment) == ('999008881', 2, environments.TEST)
    assert client.currency == 840


def test_the_setting_is_not_mutated(settings):
    get_client()
    assert 'secret_key' in settings.REDSYS_CLIENT


@pytest.mark.parametrize(
    'value',
    [
        None,
        {},
        {'merchant_code': '999008881'},
        {'secret_key': 'secret', 'colour': 'red'},
        {'secret_key': 'secret', 'environment': 'MARS'},
        {'api_key': 'not an api key'},
        {'api_key': f'{environments.TEST}_{urlsafe_b64encode(b"999008881_2_secret").decode()}', 'terminal': 3},
    ],
)
def test_missing_secret_is_a_configuration_error(settings, value):
    settings.REDSYS_CLIENT = value
    with pytest.raises(ImproperlyConfigured):
        get_client()
