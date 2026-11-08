from ipaddress import ip_network

from django.conf import settings


def notification_networks():
    """The networks of ``REDSYS_NOTIFICATION_IPS``, or ``None`` when the setting is absent or empty."""
    entries = getattr(settings, 'REDSYS_NOTIFICATION_IPS', None)
    if not entries:
        return None
    if not isinstance(entries, (list, tuple)) or not all(isinstance(entry, str) for entry in entries):
        raise TypeError('it must be a list of strings.')
    return [ip_network(entry, strict=False) for entry in entries]
