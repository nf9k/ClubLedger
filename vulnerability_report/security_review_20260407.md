# ClubLedger Security Review — 04/07/2026

## Critical

1. **Open Redirect** (`app.py:254, 987, 1027-1031`) — The `next` parameter from the login form is stored in the session without validation and used in `redirect()` after 2FA. An attacker can craft `/login?next=https://evil.com` to redirect users post-auth. Fix: validate that redirect URLs are relative or same-origin before storing.

2. **XSS in ZIP Lookup** (`static/js/app.js:49-57`) — City/state values from the database are concatenated into HTML strings and injected via `innerHTML` in onclick handlers. A crafted city name like `"; alert('XSS'); "` breaks the onclick attribute. Fix: use DOM methods (`createElement`, `textContent`, `addEventListener`) instead of string concatenation.

## High

3. **No CSRF Protection** (all POST routes) — No Flask-WTF or CSRF tokens on any forms. An attacker can craft a page that causes authenticated users to delete members, modify profiles, or disable 2FA. Fix: add `CSRFProtect(app)` from Flask-WTF and `{{ csrf_token() }}` to all forms.

4. **No Rate Limiting** (`app.py:230, 737, 932`) — Login, password reset, and 2FA challenge endpoints accept unlimited attempts. Fix: add Flask-Limiter with per-IP limits (e.g. 5/min on login, 3/min on reset).

5. **Demo Reset Runs Raw SQL** (`app.py:1202-1232`) — The `/demo/reset` endpoint executes SQL from `seed.sql`. If DEMO_MODE is accidentally enabled in production, this truncates and reseeds the database. Fix: add additional safeguards or remove from production builds.

6. **2FA Session Not Regenerated** (`app.py:253-254, 987-989`) — After successful 2FA, the session ID is not regenerated, allowing potential session fixation. Fix: regenerate the session after 2FA completion.

## Medium

7. **ZIP Lookup Unauthenticated** (`app.py:876-890`) — `/zip-lookup/<zip_code>` has no `@login_required`. Fix: add the decorator.

8. **Missing Secure Cookie Flags** (`app.py:14-16`) — `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, and `SESSION_COOKIE_SAMESITE` are not set. Fix: set `HTTPONLY=True`, `SAMESITE='Lax'`, and `SECURE=True` in production.

9. **console.log in Production** (`dashboard.html:185-223`) — Debug logging leaks email addresses and application flow to browser console. Fix: remove all console.log statements.

10. **Print Statements for Errors** (`app.py:190, 220`) — Errors printed to stdout instead of using proper logging. Fix: use `app.logger.error()`.

## Low

11. **Default SECRET_KEY Fallback** (`app.py:15`) — Falls back to `'dev-secret-key-change-in-production'` if env var unset. Fix: raise an error if SECRET_KEY is not set.

## Passing

- All SQL queries use parameterized queries (`%s` placeholders) — no SQL injection
- Passwords hashed with bcrypt
- TOTP and WebAuthn 2FA properly implemented
- Backup codes bcrypt-hashed
- Admin routes use `@admin_required` decorator
- Jinja2 auto-escaping enabled
- Email constructed via Flask-Mail API — no header injection
