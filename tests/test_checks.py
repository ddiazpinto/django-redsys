import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError

from django_redsys.checks import check_deploy, check_settings


def _ids(messages):
    return [message.id for message in messages]


def test_valid_settings_pass():
    assert check_settings(None) == []
    call_command('check')


@pytest.mark.parametrize('value', [None, {'secret_key': 'secret', 'colour': 'red'}])
def test_invalid_client_setting_is_e001(settings, value):
    settings.REDSYS_CLIENT = value
    assert _ids(check_settings(None)) == ['django_redsys.E001']
    with pytest.raises(SystemCheckError):
        call_command('check')


@pytest.mark.parametrize('value', [['not an address'], ['192.0.2.0/33'], [7], '192.0.2.1'])
def test_invalid_notification_ips_is_e002(settings, value):
    settings.REDSYS_NOTIFICATION_IPS = value
    assert _ids(check_settings(None)) == ['django_redsys.E002']


def test_test_environment_without_debug_warns_on_deploy(settings):
    settings.DEBUG = False
    assert _ids(check_deploy(None)) == ['django_redsys.W001']


@pytest.mark.parametrize(
    ('debug', 'client'),
    [
        (True, {'secret_key': 'secret', 'sandbox': True}),
        (False, {'secret_key': 'secret'}),
        (False, {'secret_key': 'secret', 'sandbox': False}),
        (False, None),
    ],
)
def test_no_deploy_warning(settings, debug, client):
    settings.DEBUG, settings.REDSYS_CLIENT = debug, client
    assert check_deploy(None) == []
