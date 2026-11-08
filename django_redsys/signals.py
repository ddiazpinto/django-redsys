from django.dispatch import Signal

request_created = Signal()
notification_received = Signal()
notification_authorized = Signal()
notification_denied = Signal()
notification_invalid = Signal()
