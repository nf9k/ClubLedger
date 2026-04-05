# Membership Portal — Quick Reference

## Project Layout

```
membership-portal/
├── app/
│   ├── app.py              ← Flask application
│   └── static/             ← Logo and static assets
├── templates/              ← HTML templates
├── database/               ← SQL migrations
├── scripts/                ← Cron and backup scripts
├── documentation/          ← Admin and member guides
└── tests/
    └── test_data_setup.sql ← Test accounts
```

---

## Quick Deployment (5 Steps)

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set SECRET_KEY, DB credentials, SMTP, APP_URL, ORG_NAME

# 2. Start containers
docker compose up -d --build

# 3. Apply database migrations
source .env
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_admin_comments.sql
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_expiration_tracking.sql

# 4. Create first admin (replace values as needed)
docker exec -it clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}"
# Then run:
# INSERT INTO members (call_sign, password_hash, email, name, is_admin)
# VALUES ('W9ABC', '<bcrypt-hash>', 'admin@yourclub.org', 'Your Name', 1);

# 5. Verify
curl -I http://localhost:5000
```

---

## Org Branding (.env)

```env
ORG_NAME=Your Club Name
SERVICE_DESK_URL=help.yourclub.org
LOGO_FILENAME=logo.png
ADMIN_EMAILS=admin@yourclub.org,other@yourclub.org
```

`ORG_NAME` flows into the navbar, page titles, all email subjects and bodies, and the PDF header. If `LOGO_FILENAME` is omitted, the org name renders as text on the login page. If `SERVICE_DESK_URL` is omitted, emails use generic "contact an administrator" text.

---

## Feature Summary

| Feature | Description |
|---------|-------------|
| **Call Sign Login** | Members log in with call sign + password |
| **Record Change Emails** | Members receive a field-by-field diff whenever their record is saved |
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
☐ Call signs are clickable links
☐ Save a profile change — member receives diff email
☐ Expiration cron set up (optional)
```

---

## Optional: Expiration Notifications

```bash
# Schedule daily checks at 9 AM
crontab -e
# Add:
0 9 * * * /path/to/membership-portal/scripts/run_expiration_check.sh >> /path/to/membership-portal/backups/expiration_check.log 2>&1
```

Requires `ADMIN_EMAILS` set in `.env` to receive summary reports.

---

## Rollback

```bash
docker compose down
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" < backup.sql
docker compose up -d
```

---

## Security Notes

- Passwords are bcrypt-hashed — admins never see them
- Admin comments are stored in the database and not exposed to members
- SMTP credentials live in `.env` — never commit that file
- Session timeout: 24 hours
- All SQL queries use parameterised placeholders

---

## System Requirements

- Docker & Docker Compose
- MariaDB 11
- Python 3.9+
- SMTP server access
- 100 MB disk space minimum
