# Templates

django-redsys renders three templates. They are plain standalone pages, meant to be replaced by the project's own.

| Template | Rendered by | Context | Blocks |
|---|---|---|---|
| `django_redsys/redirect.html` | Payment views (`RedsysPaymentMixin.redirect_to_redsys()`) | `endpoint`: the RedSys URL the form posts to; `fields`: a dict of the three `Ds_*` fields | `title`, `head`, `content` |
| `django_redsys/ok.html` | `ResultView` at `django_redsys:ok` | `redsys_response`: the verified python-redsys `Response`, authorized | `title`, `content` |
| `django_redsys/ko.html` | `ResultView` at `django_redsys:ko` | `redsys_response`: the verified python-redsys `Response`, not authorized | `title`, `content` |

All three also receive `view` and whatever the project's context processors add. The OK and KO pages are only rendered with a verified result; without one they answer `404` (see the README, "OK and KO pages").

## Where an override goes

Django's template loaders search the `DIRS` of `TEMPLATES` first, then the `templates/` directory of each app in `INSTALLED_APPS` order. A template at the same path in either place wins over the app's:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # templates/django_redsys/ok.html replaces the app's
        'APP_DIRS': True,
        ...
    }
]
```

Or, in an app of the project listed before `django_redsys`:

```python
INSTALLED_APPS = [..., 'shop', 'django_redsys']  # shop/templates/django_redsys/ok.html replaces the app's
```

## Replace a page with the site's layout

The usual override extends the project's base template and uses the context of the table:

```django
{# templates/django_redsys/ok.html #}
{% extends "base.html" %}

{% block content %}
<h1>Payment completed</h1>
<p>Order {{ redsys_response.order }}: {{ redsys_response.amount }} paid.</p>
{% endblock %}
```

```django
{# templates/django_redsys/ko.html #}
{% extends "base.html" %}

{% block content %}
<h1>The payment was not completed</h1>
<p>Order {{ redsys_response.order }}. No charge was made.</p>
<p><a href="{% url 'cart' %}">Back to the cart</a></p>
{% endblock %}
```

`redsys_response` carries every result field (`order`, `amount`, `currency`, `response_code`, `authorization_code`, `merchant_data`, ...); `redsys_response.describe` with no argument gives the meaning of the code in Spanish. The [python-redsys response reference](https://github.com/ddiazpinto/python-redsys/blob/master/docs/redirect-connection.md#response-parameters) lists them.

## Change only some blocks

An override can extend the template it replaces, by the same name, and change only some blocks; `{{ block.super }}` keeps the original content of a block:

```django
{# templates/django_redsys/redirect.html #}
{% extends "django_redsys/redirect.html" %}

{% block title %}Redirecting to the bank{% endblock %}
{% block head %}<link rel="stylesheet" href="/static/payment.css">{% endblock %}
```

```django
{# templates/django_redsys/ok.html #}
{% extends "django_redsys/ok.html" %}

{% block content %}{{ block.super }}<p>Thank you for your order.</p>{% endblock %}
```

## Replace the redirect page entirely

The redirect page carries the signed request; a replacement that does not extend the original keeps its three parts: a form that posts to `endpoint`, one hidden input per item of `fields`, and something that submits it (the original uses an inline script and a `<noscript>` button):

```django
{# templates/django_redsys/redirect.html #}
{% extends "base.html" %}

{% block content %}
<form id="redsys" method="post" action="{{ endpoint }}">
  {% for name, value in fields.items %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
  <button type="submit">Continue to the payment page</button>
</form>
{% endblock %}
```

The form posts to RedSys, not to the project, so it carries no CSRF token.

## Another template for one view

- A payment view sets `redirect_template_name`.
- The OK and KO pages are views of the app; a page with its own template routes `ResultView` under the project's URLs and points `url_ok` or `url_ko` at it from `get_redsys_fields()`:

```python
# urls.py
from django_redsys.views import ResultView

path('shop/paid/', ResultView.as_view(template_name='shop/paid.html'), name='paid'),
path('shop/not-paid/', ResultView.as_view(template_name='shop/not-paid.html', authorized=False), name='not-paid'),
```

```python
# the payment view
def get_redsys_fields(self):
    return {
        ...,
        'url_ok': self.request.build_absolute_uri(reverse('paid')),
        'url_ko': self.request.build_absolute_uri(reverse('not-paid')),
    }
```

## Translations

The app's templates mark their text with `{% translate %}` and set `lang` from the active language. The package ships no translations yet; a project translates the strings in its own catalog or replaces the templates.

## Content Security Policy

The original `redirect.html` submits the form with an inline script. With Django's CSP middleware (Django 6.0 and later) and the `django.template.context_processors.csp` context processor, the script carries the request's nonce; the policy then needs `CSP.NONCE` in `script-src` and the RedSys host in `form-action`:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    'script-src': [CSP.SELF, CSP.NONCE],
    'form-action': [CSP.SELF, 'https://sis.redsys.es', 'https://sis-t.redsys.es:25443'],
}
```

A replacement with its own inline script adds `{% if csp_nonce is not None %} nonce="{{ csp_nonce }}"{% endif %}` to the `<script>` tag, as the original does.
