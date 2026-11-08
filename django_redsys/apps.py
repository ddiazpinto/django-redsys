from django.apps import AppConfig


class DjangoRedsysConfig(AppConfig):
    name = 'django_redsys'
    verbose_name = 'RedSys'

    def ready(self):
        from . import checks  # noqa: F401
