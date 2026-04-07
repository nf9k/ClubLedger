# ClubLedger — Quick Reference

## Project Layout

```
clubledger/
├── app/
│   ├── app.py              ← Flask application (all routes)
│   ├── twofa.py            ← 2FA helpers
│   └── requirements.txt
├── templates/              ← Jinja2 HTML templates
│   └── twofa/              ← 2FA-specific templates
├── static/                 ← Logo and assets (volume-mounted)
├── database/               ← schema.sql + migration files
├── scripts/                ← FCC import, expiration check, backup
├── documentation/          ← Admin and member guides
├── Dockerfile
└── docker-compose.yml
```

---

## Fresh Install (5 Steps)

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set SECRET_KEY, DB credentials, SMTP, APP_URL, ORG_NAME

# 2. Start containers (schema applied automatically)
docker compose up -d

# 3. Create first admin
docker exec -it clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}"
# INSERT INTO members (call_sign, password_hash, email, name, is_admin)
# VALUES ('W9ABC', '<bcrypt-hash>', 'admin@yourclub.org', 'Your Name', 1);

# Generate bcrypt hash:
# python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"

# 4. Verify
curl -I http://localhost:5000

# 5. (Optional) Import FCC data
docker exec clubledger_web python3 /app/scripts/import_fcc.py
```

---

## Upgrading

```bash
# Run any new migration(s) first, then pull and restart
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_2fa.sql
docker compose pull web && docker compose up -d --force-recreate web
```

---

## Org Branding (.env)

```env
ORG_NAME=Your Club Name
SERVICE_DESK_URL=help.yourclub.org
LOGO_FILENAME=logo.png
ADMIN_EMAILS=admin@yourclub.org,other@yourclub.org
```

`ORG_NAME` flows into the navbar, page titles, all email subjects/bodies, and the PDF header. `APP_URL` is used to derive the WebAuthn origin for 2FA security keys — must be the exact URL members use to reach the site.

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| **Call Sign Login** | Members log in with call sign + password |
| **hCaptcha** | Bot protection on login and password recovery (optional) |
| **Two-Factor Auth** | TOTP app, YubiKey/WebAuthn, or backup codes |
| **FCC Lookup** | Admin looks up any call sign; one-click sync to profile |
| **Record Change Emails** | Members receive a field-by-field diff on every save |
| **Admin Comments** | 500-char internal notes field, invisible to members |
| **PDF Export** | Roster sorted by last name, landscape format |
| **Call Sign Edit** | Admins can change member call signs |
| **Expiration Notifications** | Auto-email on status change (Active/Expiring/Expired) |
| **Password Reset** | Email-based token, 24-hour expiry |
| **Sortable Dashboard** | Click column headers to sort |

---

## Post-Deployment Checklist

```
☐ Login as admin works
☐ Add new member — auto-sends password reset email
☐ Admin comments field visible (admins only)
☐ PDF export downloads and sorts by last name
☐ Status badges show correct colours
☐ Save a profile change — member receives diff email
☐ hCaptcha widget visible on login and password recovery (if keys configured)
☐ Security & 2FA page accessible from user dropdown
☐ TOTP setup works end-to-end
☐ FCC lookup populates name/address on Add Member
☐ Expiration cron set up (optional)
☐ FCC daily import cron set up (optional)
```

---

## Cron Jobs

```bash
# Expiration notifications — daily at 9 AM
0 9 * * * docker exec clubledger_web python3 /app/scripts/check_expirations.py >> /var/log/clubledger_expirations.log 2>&1

# FCC incremental update — daily at 3 AM
0 3 * * * docker exec clubledger_web python3 /app/scripts/import_fcc.py --daily >> /var/log/fcc_import.log 2>&1
```

---

## Security Notes

- Passwords are bcrypt-hashed — admins never see them
- hCaptcha protects login and password recovery from bots — inactive unless both keys are set in `.env` and compose `environment:`
- 2FA backup codes are individually bcrypt-hashed and single-use
- WebAuthn origin is derived from `APP_URL` — must match the browser-facing URL exactly
- Admin comments are not exposed to members via any route
- SMTP credentials live in `.env` — never commit that file
- Session timeout: 24 hours
- All SQL queries use parameterised placeholders

---

## System Requirements

- Docker & Docker Compose
- MariaDB 11
- SMTP server access
