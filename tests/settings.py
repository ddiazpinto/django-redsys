from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = 'tests'
ROOT_URLCONF = 'tests.urls'
ALLOWED_HOSTS = ['testserver']
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.auth', 'redsys_gateway']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
USE_TZ = True
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
    }
]

# The public credentials of the RedSys test environment.
REDSYS_CLIENT = {
    'secret_key': 'sq7HjrUOBfKmC576ILgskD5srU870gJ7',
    'merchant_code': '999008881',
    'terminal': 1,
    'sandbox': True,
}
