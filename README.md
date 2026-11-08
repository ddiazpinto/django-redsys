# django-redsys

[![CI](https://github.com/ddiazpinto/django-redsys/actions/workflows/ci.yml/badge.svg)](https://github.com/ddiazpinto/django-redsys/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/django-redsys.svg)](https://pypi.org/project/django-redsys/) ![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg) ![Django 5.2+](https://img.shields.io/badge/django-5.2%2B-blue.svg) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

Django views, URLs and signals for RedSys TPV Virtual payments over the *redirect connection*. Signing, verification, parameters, constants and response codes come from [python-redsys](https://github.com/ddiazpinto/python-redsys); this app adds the Django side: the page that sends the cardholder to RedSys, the endpoint that receives RedSys's notification, the OK and KO pages, and signals.

## Installation

```bash
pip install django-redsys
```

```python
# settings.py
INSTALLED_APPS = [..., 'django_redsys']

REDSYS_CLIENT = {
    'secret_key': '...',
    'merchant_code': '999008881',
    'terminal': 1,
    'sandbox': True,
}

# urls.py
urlpatterns = [..., path('redsys/', include('django_redsys.urls'))]
```

## Settings

| Setting | Use |
|---|---|
| `REDSYS_CLIENT` | Required. The account: the keyword options of python-redsys's `RedirectClient`. |
| `REDSYS_NOTIFICATION_IPS` | Optional. Addresses or networks allowed to post notifications; see [Notification senders](#notification-senders). |

The keys of `REDSYS_CLIENT`:

| Key | Use |
|---|---|
| `secret_key` | Merchant secret key. Required unless `api_key` is set. |
| `merchant_code`, `terminal` | Merchant code (FUC) and terminal number. |
| `sandbox` or `environment` | `sandbox=True` targets the test environment; `environment=` takes `redsys.environments.TEST`, `PROD`, `INTE` or `DESA`. Production by default. |
| `currency` | Default currency (`redsys.currencies`); the euro unless set. |
| `signature_version` | `HMAC_SHA512_V2` by default. |
| `module` | `Ds_Merchant_Module` of every request. |
| `api_key` | A RedSys API key, read with `RedirectClient.from_api_key()`; replaces `secret_key`, `merchant_code`, `terminal` and the environment. |

The keys go to the constructor unchanged, so an option a later python-redsys adds works without a django-redsys release. An unknown key, an invalid value, or `api_key` together with the values it replaces raises `ImproperlyConfigured`. See the [python-redsys configuration](https://github.com/ddiazpinto/python-redsys#configuration).

`manage.py check` validates both settings (`django_redsys.E001`, `django_redsys.E002`). `manage.py check --deploy` warns when `REDSYS_CLIENT` targets an environment other than production while `DEBUG` is off (`django_redsys.W001`); a staging server that uses the test environment on purpose silences it with `SILENCED_SYSTEM_CHECKS`.

## Payment view

A subclass of `RedsysPaymentView` returns the operation fields; the view signs them and renders a form that posts itself to RedSys. It answers GET and POST. A view that stores state, as the one below, is reached through a POST form (a "Pay" button): browsers and crawlers prefetch GET links, and each prefetch would use up an order number.

```python
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django_redsys.views import RedsysPaymentView
from redsys import generate_order


class PayOrderView(RedsysPaymentView):
    def get_redsys_fields(self):
        order = get_object_or_404(Order, pk=self.kwargs['pk'], user=self.request.user)
        order.redsys_order = generate_order()
        order.save(update_fields=['redsys_order'])
        return {
            'order': order.redsys_order,
            'amount': order.total,  # Decimal, in euros unless currency= says otherwise
            'merchant_data': str(order.pk),
            'product_description': 'Online order',
        }
```

| Attribute or method | Use |
|---|---|
| `get_redsys_fields()` | Required. The keyword fields of the operation: `order`, `amount` and any other [redirect parameter](https://github.com/ddiazpinto/python-redsys/blob/master/docs/redirect-connection.md). `None` (or `Http404` raised) when there is no order to pay: the view answers `404`. |
| `get_redsys_client()` | The client that signs, `get_client()` by default. A view that pays through another terminal or merchant returns its own `RedirectClient`; the notification and result views have the same method. |
| `transaction_type` | `redsys.transactions.AUTHORIZATION` by default; `PREAUTHORIZATION`, `AUTHENTICATION` or `REFUND_WITHOUT_ORIGINAL` for the other redirect operations. |
| `redirect_template_name` | `django_redsys/redirect.html` by default. |
| `get_redsys_request()` | Builds and signs the python-redsys `Request`; sends `request_created`. |

`merchant_url`, `url_ok` and `url_ko` default to the app's notification, OK and KO URLs; a value returned by `get_redsys_fields()` replaces them. The URLs are absolute, from `request.build_absolute_uri()`; behind a proxy that terminates TLS, `SECURE_PROXY_SSL_HEADER` makes them `https`.

The page is sent with `Cache-Control: no-store`: a cached copy would post an order number RedSys already received, which it rejects (SIS0051).

`RedsysPaymentFormView` is the same on top of `FormView`: after `form_valid()`, `self.form` holds the validated form for `get_redsys_fields()`. `RedsysPaymentMixin` holds the behavior for other view classes; `redirect_to_redsys()` returns the response.

Invalid fields raise python-redsys's `ValueError` subclasses before anything is signed ([errors](https://github.com/ddiazpinto/python-redsys#errors)).

## Notification and signals

RedSys posts the result of every operation to `merchant_url`. `NotificationView` (`django_redsys:notification`) verifies the signature, parses the result into a python-redsys `Response` and sends the signals; it answers `200` with an empty body. A payload that fails parsing or verification, whatever the exception, raises `SuspiciousOperation` chained to it: Django answers `400` and logs it on the `django.security` logger.

| Signal (`django_redsys.signals`) | Sent | Arguments |
|---|---|---|
| `request_created` | A payment view signed a request. | `request`, `redsys_request`, `fields` |
| `notification_received` | A notification passed verification. | `request`, `response` |
| `notification_authorized` | After `notification_received`, when `response.is_authorized()`. | `request`, `response` |
| `notification_denied` | After `notification_received`, otherwise. | `request`, `response` |
| `notification_invalid` | A notification failed verification or parsing, or came from an address outside `REDSYS_NOTIFICATION_IPS`. | `request`, `error` |
| `notification_repeated` | With [the notification record](#notification-record), a verified notification whose payload already arrived; sent instead of the three above. | `request`, `response` |

`sender` is the view class. The notification is the source of truth for an operation's outcome; the OK and KO pages are not, since the cardholder may never reach them.

A valid notification can arrive more than once. The signed result also reaches the cardholder's browser on the redirect to `url_ok` or `url_ko` (when the portal sends it, see below), and a copy posted to the notification URL verifies like the original. Receivers are idempotent: they act on the state of the order, not on the arrival of the signal, and check that the result matches what was asked for.

```python
from django.db import transaction
from django.dispatch import receiver
from django_redsys.signals import notification_authorized


@receiver(notification_authorized)
def mark_paid(sender, request, response, **kwargs):
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(redsys_order=response.order).first()
        if order is None or order.is_paid or order.total != response.amount:
            return
        order.mark_paid(authorization_code=response.authorization_code)
```

`response` carries every result field (`order`, `amount`, `response_code`, `authorization_code`, `merchant_data`, `card_country`, ...) and `response.describe(language)` gives the meaning of the code; see the [response parameters](https://github.com/ddiazpinto/python-redsys/blob/master/docs/redirect-connection.md#response-parameters) and [response codes](https://github.com/ddiazpinto/python-redsys/blob/master/docs/response-codes.md). An exception in a receiver propagates, and the notification gets a `500`.

## Notification senders

`REDSYS_NOTIFICATION_IPS`, off by default, limits who may post to the notification URL. A request from any other address gets `403` before its payload is parsed, and `notification_invalid` is sent with a `PermissionDenied` error.

```python
REDSYS_NOTIFICATION_IPS = ['192.0.2.10', '198.51.100.0/24']  # RedSys's addresses, as the bank or RedSys gives them
```

The address compared is `REMOTE_ADDR`. Behind a proxy or load balancer, `REMOTE_ADDR` is the proxy's unless the server sets it from the forwarded header; a subclass of `NotificationView` can override `is_allowed_sender()` to read it another way. The signature check stays: the list only saves the work of parsing what does not come from RedSys.

## Notification record

`django_redsys.notifications`, an optional app, records every verified notification and turns a repeat into `notification_repeated`:

```python
INSTALLED_APPS = [..., 'django_redsys', 'django_redsys.notifications']
```

```bash
python manage.py migrate
```

- A notification is a repeat when its `Ds_MerchantParameters` is identical to one already recorded (SHA-256 digest, unique). A new result for the same order is not a repeat. Idempotency per order stays with the receivers.
- The record and the signals commit in one transaction on the database the model is routed to: a receiver that raises leaves nothing recorded, and the next arrival of the same notification is processed as new.
- Each record keeps the order, the response code and `SISnnnn` error code, whether it was authorized, the amount and currency, the transaction type, the authorization code, the merchant code, terminal and environment (`TEST`, `PROD`, ...), whether the payment was 3-D Secure authenticated (`Ds_SecurePayment`), the payment method that processed it (`Ds_ProcessedPayMethod`), RedSys's date and hour as sent (`Ds_Date`, `Ds_Hour`), the sender address, the first and last arrival, and the number of arrivals. Card data, stored-card tokens (`Ds_Merchant_Identifier`, `Ds_Merchant_Cof_Txnid`) and `merchant_data` are not stored: a token charges the card again, and `merchant_data` is free text. Invalid notifications are not recorded.
- The admin lists the records read-only (`django.contrib.admin` installed). `python manage.py purge_redsys_notifications --older-than DAYS` deletes the records first received more than `DAYS` days ago, for a retention period run from cron or a scheduler.
- The app label is `django_redsys_notifications`.

## OK and KO pages

`django_redsys:ok` and `django_redsys:ko` render `django_redsys/ok.html` and `django_redsys/ko.html` through `ResultView`, with the verified result as `redsys_response`. RedSys appends the signed result to the redirect only when the option "Enviar Parámetros en las URLs" is on in its portal. Without a result that verifies, or with an outcome that does not match the page (an authorized result on the KO page, or the reverse), the page answers `404`. With the option off, `url_ok` and `url_ko` point to the project's own views. The pages' look is the project's: see [Templates](#templates).

## Templates

| Template | Rendered by | Context |
|---|---|---|
| `django_redsys/redirect.html` | Payment views | `endpoint`, `fields` (the three `Ds_*` fields) |
| `django_redsys/ok.html` | `django_redsys:ok` | `redsys_response` |
| `django_redsys/ko.html` | `django_redsys:ko` | `redsys_response` |

The app's templates are plain standalone pages. A template at the same path in a directory of the `DIRS` option of `TEMPLATES`, or in an app listed before `django_redsys` in `INSTALLED_APPS`, replaces the app's, usually extending the project's base template:

```django
{# templates/django_redsys/ok.html #}
{% extends "base.html" %}

{% block content %}
<h1>Payment completed</h1>
<p>Order {{ redsys_response.order }}: {{ redsys_response.amount }} paid.</p>
{% endblock %}
```

Changing only some blocks, replacing the redirect page, a template per view, translations and the Content Security Policy of the redirect page: [`docs/templates.md`](https://github.com/ddiazpinto/django-redsys/blob/master/docs/templates.md).

## Direct operations

`django_redsys.client.get_client()` builds the client from `REDSYS_CLIENT`; it takes another client class for the direct connection (`pip install "python-redsys[http]"`):

```python
from django_redsys.client import get_client
from redsys.clients import DirectClient

response = get_client(DirectClient).refund(order=order.redsys_order, amount=order.total).send()
response.is_refunded()
```

## Compatibility

| | |
|---|---|
| Version | 1.0.1 |
| Django | 5.2 LTS, 6.0 and 6.1 |
| Python | 3.10 to 3.15 (Django 6.0 and later need 3.12) |
| python-redsys | 2.2 and later |

Upgrading from 0.4: [`docs/migration-0.4-to-1.0.md`](https://github.com/ddiazpinto/django-redsys/blob/master/docs/migration-0.4-to-1.0.md).

## Development

```bash
uv sync
uv run pytest
uv run ruff check django_redsys tests && uv run ruff format --check django_redsys tests
```

## License

Apache License 2.0, as python-redsys. See [`LICENSE`](https://github.com/ddiazpinto/django-redsys/blob/master/LICENSE) and [`NOTICE`](https://github.com/ddiazpinto/django-redsys/blob/master/NOTICE). Releases up to 0.4.2 were published under the MIT License.
