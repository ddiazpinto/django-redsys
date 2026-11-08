from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = 'tests'
ROOT_URLCONF = 'tests.urls'
ALLOWED_HOSTS = ['testserver']
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django_redsys',
    'django_redsys.notifications',
]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
USE_TZ = True
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }
]
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# The public credentials of the RedSys test environment.
REDSYS_CLIENT = {
    'secret_key': 'sq7HjrUOBfKmC576ILgskD5srU870gJ7',
    'merchant_code': '999008881',
    'terminal': 1,
    'sandbox': True,
}
