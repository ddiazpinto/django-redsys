# Security policy

`django-redsys` receives and acts on RedSys TPV Virtual payment notifications in Django projects. Reports are handled with priority.

## Supported versions

| Version | Status | Supported until |
|---------|--------|-----------------|
| 1.x | Active, all fixes | ongoing |
| < 1.0 | End of life | n/a |

## Reporting a vulnerability

Do not open a public issue. Report privately through GitHub: *Security*, then *Report a vulnerability*, on <https://github.com/ddiazpinto/django-redsys/security/advisories>, or email the maintainer listed in the package metadata. A vulnerability in signing or verification itself belongs to [python-redsys](https://github.com/ddiazpinto/python-redsys/security/advisories).

Include the affected versions, the impact, a minimal reproduction and any suggested fix. Reports are acknowledged within a few days; the fix is released in coordination with the reporter, who is credited with their permission.

## Security model

The app renders the signed payment form, verifies notifications and the OK and KO redirects through python-redsys, and sends signals. Signing and verification are python-redsys's. The integrator is responsible for:

- **Secret key:** keeping `REDSYS_CLIENT` out of source control, logs and error reports.
- **Idempotent receivers:** a valid notification can arrive more than once, and the cardholder can see its signed copy on the redirect to `url_ok` or `url_ko`; receivers act on the state of the order and check the amount (see the README).
- **Acting on the notification:** the outcome of a payment comes from the notification signals, not from the OK and KO pages.
- **Proxies:** `REDSYS_NOTIFICATION_IPS` compares `REMOTE_ADDR`, which behind a proxy is the proxy's unless the server sets it from the forwarded header.
- **Transport:** serving the notification and redirect URLs over HTTPS.
