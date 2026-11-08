# Migration from 0.4 to 1.0

1.0 is a rewrite on python-redsys 2.2 and Django 5.2 or later. The package, the settings, the views, the URLs and the signals change; nothing from 0.4 keeps working unchanged. The protocol changes too: python-redsys 2.x signs with `HMAC_SHA512_V2` by default, and its request fields replace the 0.2.5 attributes ([python-redsys migration guide](https://github.com/ddiazpinto/python-redsys/blob/master/docs/migration-1x-to-2x.md)).

## Package

| 0.4 | 1.0 |
|---|---|
| `pip install` from the git repository | `pip install django-redsys` |
| `'redsys_gateway'` in `INSTALLED_APPS` | `'django_redsys'` |
| `include('redsys_gateway.urls')`, namespace `redsys_gateway` | `include('django_redsys.urls')`, namespace `django_redsys` |
| Templates under `redsys_gateway/` | Templates under `django_redsys/` |

## Templates

An override with an old name or block is not an error: Django renders the app's template, or ignores the unknown block.

| 0.4 | 1.0 |
|---|---|
| `redsys_gateway/redirect.html` | `django_redsys/redirect.html` |
| `redsys_gateway/accepted.html` | `django_redsys/ok.html` |
| `redsys_gateway/rejected.html` | `django_redsys/ko.html` |
| Block `headers` in `redirect.html` | Block `head` |
| Block `form` in `redirect.html` | Removed; the form is in block `content` |
| Context `Ds_SignatureVersion`, `Ds_MerchantParameters`, `Ds_Signature` | `fields`, a dict of the three; `endpoint` as before |
| No context on the result pages | `redsys_response`, the verified result |

## Settings

The client options move into one dict, `REDSYS_CLIENT`; per-operation values move into the payment view's `get_redsys_fields()`.

| 0.4 | 1.0 |
|---|---|
| `REDSYS_SECRET_KEY` | `REDSYS_CLIENT['secret_key']` |
| `REDSYS_SANDBOX` | `REDSYS_CLIENT['sandbox']` |
| `REDSYS_MERCHANT_CODE` | `REDSYS_CLIENT['merchant_code']` |
| `REDSYS_TERMINAL` | `REDSYS_CLIENT['terminal']` |
| `REDSYS_CURRENCY` | `REDSYS_CLIENT['currency']`; the euro unless set |
| `REDSYS_TRANSACTIONTYPE` | `transaction_type` on the payment view |
| `REDSYS_MERCHANT_NAME`, `REDSYS_TITULAR`, `REDSYS_PRODUCT_DESCRIPTION` | `merchant_name`, `titular`, `product_description` in `get_redsys_fields()` |
| `REDSYS_REDIRECT_VIEW` | Removed: the project routes its own payment view. |
| `REDSYS_TRANSACTION_ACCEPTED_VIEW`, `REDSYS_TRANSACTION_REJECTED_VIEW` | Removed: `url_ok` and `url_ko` in `get_redsys_fields()` point at any view, or the project overrides `django_redsys/ok.html` and `ko.html`. |

## Views

| 0.4 | 1.0 |
|---|---|
| `RedsysRedirectMixin` | `RedsysPaymentMixin` |
| `RedsysRedirectTemplateView` | `RedsysPaymentView` |
| `RedsysRedirectFormView` | `RedsysPaymentFormView`; the validated form is `self.form` |
| `get_order()`, `get_amount()`, `get_merchant_data()`, `get_request_parameters()` | One `get_redsys_fields()` returning `order`, `amount`, `merchant_data` and any other field |
| `get_order_object()` | Removed; `get_redsys_fields()` loads what it needs |
| `get_redirection_template_name()` | `redirect_template_name` |
| `response_view` | `NotificationView` |
| `accepted_view`, `rejected_view` | `ResultView`, with the verified result as `redsys_response`; `404` without one, so the RedSys portal option "Enviar Parámetros en las URLs" must be on |
| `forms.GatewayForm` | Removed; python-redsys verifies the fields |

## URLs

| 0.4 name and path | 1.0 name and path |
|---|---|
| `redirect`, `redirect/` | Removed |
| `response`, `response/` | `notification`, `notification/` |
| `accepted`, `accepted/` | `ok`, `ok/` |
| `rejected`, `rejected/` | `ko`, `ko/` |

The notification URL goes in every request as `merchant_url`, so the new path needs no change in the RedSys back office unless the merchant set a notification URL there.

## Signals

| 0.4 | 1.0 |
|---|---|
| `pre_transaction(request, order_object, transaction_request)` | `request_created(request, redsys_request, fields)` |
| `post_transaction(request, transaction_response)` | `notification_received(request, response)` |
| `transaction_accepted(request, transaction_response)` | `notification_authorized(request, response)` |
| `transaction_rejected(request, transaction_response)` | `notification_denied(request, response)` |
| `invalid_response(request, form)`, `suspicious_response(request, form)` | `notification_invalid(request, error)` |

`sender` is the view class instead of `None` or the view instance. `response` is a python-redsys 2.x `Response`: `response.is_authorized()` as before, the fields as snake_case attributes (`response.order`, `response.amount` as a `Decimal`, `response.response_code` as an integer).
