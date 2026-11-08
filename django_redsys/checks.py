from django.conf import settings
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from redsys import environments

from .client import get_client
from .conf import notification_networks


@checks.register()
def check_settings(app_configs, **kwargs):
    errors = []
    try:
        get_client()
    except ImproperlyConfigured as error:
        errors.append(checks.Error(str(error), id='django_redsys.E001'))
    try:
        notification_networks()
    except (TypeError, ValueError) as error:
        errors.append(
            checks.Error(
                f'REDSYS_NOTIFICATION_IPS is not valid: {error}',
                hint='List IP addresses or networks, such as "192.0.2.10" or "192.0.2.0/24".',
                id='django_redsys.E002',
            )
        )
    return errors


@checks.register(deploy=True)
def check_deploy(app_configs, **kwargs):
    try:
        client = get_client()
    except ImproperlyConfigured:
        return []
    if settings.DEBUG or client.environment == environments.PROD:
        return []
    return [
        checks.Warning(
            f'REDSYS_CLIENT targets the {client.environment} environment with DEBUG off.',
            hint='Production payments need environment=PROD (or sandbox=False).',
            id='django_redsys.W001',
        )
    ]
