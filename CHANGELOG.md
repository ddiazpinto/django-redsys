# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-11-08

A rewrite on python-redsys 2.2 and Django 5.2 or later, published on PyPI as `django-redsys`. Upgrading from 0.4: [`docs/migration-0.4-to-1.0.md`](docs/migration-0.4-to-1.0.md).

### Added

- `REDSYS_CLIENT`: the keyword options of python-redsys's `RedirectClient`, or `api_key` for `from_api_key()`.
- `django_redsys.client.get_client()`, which builds a client from `REDSYS_CLIENT`, the direct-connection clients included.
- `RedsysPaymentView`, `RedsysPaymentFormView` and `RedsysPaymentMixin`: `get_redsys_fields()` returns the operation fields and `transaction_type` selects any redirect operation (authorization, preauthorization, authentication, refund without original). `RedsysPaymentView` answers GET and POST.
- A `REDSYS_CLIENT` the client rejects raises `ImproperlyConfigured`; a notification that fails parsing or verification, whatever the exception, answers `400`.
- `ResultView` for the OK and KO pages, with the verified result as `redsys_response`; it answers `404` without a verified result or when the outcome does not match the page.
- `get_redsys_client()` on every view, to pay or verify with another account than `REDSYS_CLIENT`; a payment view whose `get_redsys_fields()` returns `None` answers `404`.
- `REDSYS_NOTIFICATION_IPS`: an optional list of addresses and networks allowed to post notifications; others get `403` before their payload is parsed.
- System checks: `django_redsys.E001` and `E002` for invalid settings, `W001` on `check --deploy` for a non-production environment with `DEBUG` off.
- `django_redsys.notifications`, an optional app that records verified notifications (read-only admin, `purge_redsys_notifications` command) and turns a repeated payload into the `notification_repeated` signal, in one transaction with the receivers.
- The payment page is sent with `Cache-Control: no-store`, has a `<noscript>` submit button, and carries the CSP nonce of Django's CSP middleware.
- Tests, `pyproject.toml` packaging and a `uv.lock`; the source distribution carries the tests and `docs/`.
- CI on GitHub Actions: lint, migrations in sync, tests on Python 3.10 to 3.15 and on every supported Django series, the lowest declared dependencies; Dependabot for uv and the actions. A release workflow publishes a `vX.Y.Z` tag to PyPI through trusted publishing.

### Changed

- The package and app are `django_redsys` (was `redsys_gateway`), with the URL namespace and template directory of the same name.
- Requires python-redsys 2.2 or later (was 0.2.5), Django 5.2 or later (was 1.10) and Python 3.10 or later.
- `NotificationView` replaces `response_view`, at `notification/`; the OK and KO pages are at `ok/` and `ko/`.
- Signals: `request_created`, `notification_received`, `notification_authorized`, `notification_denied` and `notification_invalid` replace `pre_transaction`, `post_transaction`, `transaction_accepted`, `transaction_rejected`, `invalid_response` and `suspicious_response`.
- Licensed under the Apache License 2.0 (was MIT), as python-redsys; `NOTICE` added.
- The README is Markdown and documents the whole app; `CONTRIBUTORS.md` replaces `AUTHORS.rst` and `CONTRIBUTORS.rst`.

### Removed

- The per-field settings (`REDSYS_SECRET_KEY`, `REDSYS_MERCHANT_CODE`, ...), `REDSYS_REDIRECT_VIEW`, `REDSYS_TRANSACTION_ACCEPTED_VIEW` and `REDSYS_TRANSACTION_REJECTED_VIEW`.
- The `redirect/` URL, `GatewayForm` and `setup.py`.
- Python 2.7, 3.4 and 3.5, and Django 1.10.

## [0.4.2] - 2017-07-21

The last 0.x release, on python-redsys 0.2.5 and Django 1.10. Its history is in the git log.
