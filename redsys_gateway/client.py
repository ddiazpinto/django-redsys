from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from redsys.clients import RedirectClient


def get_client(client_class=RedirectClient):
    """A python-redsys client built from the ``REDSYS_CLIENT`` setting.

    ``REDSYS_CLIENT`` holds the client's keyword options, or ``api_key`` and the remaining
    options for ``from_api_key()``. ``client_class`` takes ``DirectClient`` or ``AsyncDirectClient``.
    """
    options = dict(getattr(settings, 'REDSYS_CLIENT', None) or {})
    if 'api_key' not in options and 'secret_key' not in options:
        raise ImproperlyConfigured('REDSYS_CLIENT must set secret_key or api_key.')
    try:
        if 'api_key' in options:
            return client_class.from_api_key(options.pop('api_key'), **options)
        return client_class(options.pop('secret_key'), **options)
    except (TypeError, ValueError) as error:
        raise ImproperlyConfigured(f'REDSYS_CLIENT is not valid: {error}') from error
