# ClubLedger — Ham Radio Club Membership Portal

A self-hosted web application for managing ham radio club membership records. Members log in with their call sign to view and update their own information. Administrators manage the full member list, track dues, export rosters, and receive automated expiration notifications.

**Current version: 2.3**

---

## Features

- Call sign + password authentication with bcrypt
- Member self-service: update contact details, change password
- Admin dashboard with sortable columns and status badges (Active / Expiring / Expired)
- Add, edit, and delete members
- Automatic record change emails — members receive a field-by-field diff whenever their record is saved
- Automated expiration notifications via cron — emails sent only when status actually changes
- PDF roster export, sorted by last name
- Admin-only internal comments field (not visible to members)
- Password reset via email link (24-hour tokens)
- Fully configurable org branding via environment variables

---

## Stack

- **Backend**: Python 3 / Flask, Flask-Login, Flask-Mail
- **Database**: MariaDB
- **Auth**: bcrypt
- **PDF**: reportlab
- **Email**: any SMTP provider (SMTP2GO recommended)
- **Deployment**: Docker + Docker Compose

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An SMTP account (SMTP2GO or similar)

### 1. Clone and configure

```bash
git clone <repo-url> membership-portal
cd membership-portal
cp .env.example .env
```

Edit `.env` — at minimum set these values:

```env
SECRET_KEY=change-this-to-a-random-string

DB_ROOT_PASSWORD=
DB_USER=membership_user
DB_PASSWORD=
DB_NAME=clubledger_db

SMTP_HOST=mail.smtp2go.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@yourclub.org

APP_URL=https://members.yourclub.org

# Org branding
ORG_NAME=Your Club Name
SERVICE_DESK_URL=help.yourclub.org
LOGO_FILENAME=logo.png
ADMIN_EMAILS=admin1@yourclub.org,admin2@yourclub.org
```

See [Org Branding](#org-branding) below for details on the branding variables.

### 2. Add your logo (optional)

Copy your logo file into `app/static/` and set `LOGO_FILENAME` in `.env`. If omitted, the org name renders as text on the login page.

### 3. Start the containers

```bash
docker compose up -d --build
```

### 4. Initialise the database

```bash
source .env
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_admin_comments.sql
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_expiration_tracking.sql
```

### 5. Create your first admin account

```bash
docker exec -it clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}"
```

```sql
INSERT INTO members (call_sign, password_hash, email, name, is_admin)
VALUES ('W9ABC', '<bcrypt-hash>', 'admin@yourclub.org', 'Your Name', 1);
```

To generate a bcrypt hash:

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

### 6. Set up expiration notifications (optional)

Add to your server's crontab for daily 9am checks:

```bash
crontab -e
# Add:
0 9 * * * /path/to/membership-portal/scripts/run_expiration_check.sh >> /path/to/membership-portal/backups/expiration_check.log 2>&1
```

---

## Org Branding

Four environment variables control all club-specific text throughout the app, emails, and PDF exports. No code changes needed.

| Variable | Description | Default |
|----------|-------------|---------|
| `ORG_NAME` | Full organisation name | `Ham Radio Club` |
| `SERVICE_DESK_URL` | Support URL shown in emails and password recovery | *(omit for generic text)* |
| `LOGO_FILENAME` | Filename in `app/static/` for login page logo | *(omit to show org name as text)* |
| `ADMIN_EMAILS` | Comma-separated list for expiration summary emails | *(none)* |

---

## File Structure

```
membership-portal/
├── app/
│   ├── app.py              ← Flask application
│   ├── requirements.txt
│   └── static/             ← Logo and static assets
├── templates/              ← Jinja2 HTML templates
├── database/               ← SQL migration files
│   ├── add_admin_comments.sql
│   └── add_expiration_tracking.sql
├── scripts/
│   ├── check_expirations.py        ← Cron notification script
│   ├── run_expiration_check.sh
│   ├── setup_expiration_notifications.sh
│   └── backup_and_email.sh
├── documentation/          ← Administrator and member guides
├── tests/
│   └── test_data_setup.sql
└── docker-compose.yml
```

---

## Environment Variables — Full Reference

```env
# Application
SECRET_KEY=
APP_URL=

# Database
DB_HOST=db
DB_USER=membership_user
DB_PASSWORD=
DB_NAME=clubledger_db
DB_ROOT_PASSWORD=

# SMTP
SMTP_HOST=mail.smtp2go.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

# Org branding
ORG_NAME=
SERVICE_DESK_URL=
LOGO_FILENAME=
ADMIN_EMAILS=
```

---

## Rollback

```bash
docker compose down
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" < backup.sql
docker compose up -d
```

---

## Verification Checklist

After deployment:

- [ ] Login works (admin and regular member)
- [ ] Dashboard displays with sortable columns
- [ ] Adding a member sends password reset email
- [ ] Admin comments field visible on profile (admins only)
- [ ] PDF export downloads and sorts by last name
- [ ] Status badges show correct colours
- [ ] Call signs are clickable links
- [ ] Password reset emails send correctly
- [ ] Record change emails send correctly when a profile is saved

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
