from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'django_redsys.notifications'
    # The default label, "notifications", is common enough to clash with another app.
    label = 'django_redsys_notifications'
    verbose_name = 'RedSys notifications'
    default_auto_field = 'django.db.models.BigAutoField'
