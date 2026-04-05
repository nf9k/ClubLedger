# ClubLedger — Claude Code Context

## Project Overview

Self-hosted web application for managing ham radio club membership records. Members log in with their call sign to view and update their own information. Administrators manage the full member list, track dues, export rosters, and receive automated expiration notifications.

Current version tracked in `app/app.py` as `VERSION`.

## Stack

- **Backend:** Python 3 / Flask 3.0, Flask-Login, Flask-Mail
- **Database:** MariaDB (via `mysqlclient` / MySQLdb)
- **Auth:** bcrypt password hashing, Flask-Login session management
- **PDF export:** reportlab
- **Email:** SMTP via Flask-Mail (app) and smtplib (expiration script)
- **Deployment:** Docker + docker compose
- **Config:** `.env` file loaded by docker compose and `python-dotenv`

## Application Workflow

1. Members log in with **call sign** (uppercased) + password at `/login`
2. Regular members land on `/dashboard` showing only their own record
3. Admins see all members with sortable columns, action buttons, and export controls
4. New members added by admins only; secure random password auto-generated, reset link emailed
5. Password reset flow: token stored in `password_reset_tokens`, 24-hour expiry, single-use

## User Roles & Access

| Role | Access |
|------|--------|
| Regular member | View/edit own profile (no call sign, no paid_thru, no member_type, no admin_comments) |
| Admin (`is_admin = 1`) | Full dashboard, add/delete members, edit all fields, PDF export, reset passwords |

- Admins editing **their own** profile cannot change their own `is_admin` flag
- Admins changing their own call sign are automatically logged out

## Database Schema

### `members`
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK AUTO_INCREMENT | |
| call_sign | VARCHAR UNIQUE | Always stored uppercase |
| password_hash | VARCHAR | bcrypt |
| email | VARCHAR | Used for notifications and password reset |
| name | VARCHAR | Full name or organization name |
| primary_rep | VARCHAR | Primary repeater |
| rep_call | VARCHAR | Repeater call sign (uppercased) |
| address | VARCHAR | |
| city | VARCHAR | |
| state | VARCHAR | |
| zip | VARCHAR | |
| telephone | VARCHAR | |
| paid_thru | VARCHAR | Year only (e.g. `'2027'`), `'9999'` for life/honorary |
| member_type | VARCHAR | `FULL`, `ASSOCIATE`, `LIFE`, `HONORARY` |
| is_admin | TINYINT | 0 or 1 |
| admin_comments | TEXT | Admin-only notes, max 500 chars, not visible to members |
| expiration_status | VARCHAR(20) | `active`, `expiring`, `expired`, `unknown` |
| expiration_notice_sent | DATE | Date last expiration notice was sent |

### `password_reset_tokens`
| Column | Notes |
|--------|-------|
| user_id | FK to members.id |
| token | urlsafe random 32-byte token |
| expires_at | 24 hours from creation |
| used | BOOLEAN, marked TRUE after use |

### `fcc_licenses`
| Column | Notes |
|--------|-------|
| callsign | PK, uppercase |
| fname, mi, lname, suffix | Name parts |
| address, city, state, zip | Address |
| license_class | Extra, General, Technician, etc. |
| license_status | A=Active, E=Expired, C=Cancelled, T=Terminated |
| updated_at | Auto-updated on upsert |

Populated by `scripts/import_fcc.py` (weekly full or daily incremental from FCC ULS).

## Expiration Status Logic

Computed from `paid_thru` (integer year comparison):
- **active** — `paid_thru > current year`
- **expiring** — `paid_thru == current year`
- **expired** — `paid_thru < current year`
- **unknown** — null or non-numeric

`scripts/check_expirations.py` runs via cron (daily). Sends member email only when status *changes*. Also emails an admin summary to `ADMIN_EMAILS`.

## Key Routes

| Route | Auth | Description |
|-------|------|-------------|
| `/login` | Public | Call sign + password login |
| `/forgot-password` | Public | Password reset request |
| `/reset-password/<token>` | Public | Set new password via token |
| `/dashboard` | Login | Member list (admin) or own record (member) |
| `/profile/<id>` | Login | Edit profile; permission checked in handler |
| `/change-password` | Login | Change own password |
| `/admin/add-member` | Admin | Add new member, auto-sends reset email |
| `/admin/delete-member/<id>` | Admin | Delete member (cannot delete self) |
| `/admin/export-pdf` | Admin | Landscape PDF sorted by last name |
| `/admin/initiate-reset/<id>` | Admin | Send password reset email (AJAX) |
| `/admin/fcc-lookup/<callsign>` | Admin | FCC license lookup (AJAX) |

## Key Patterns

- `get_db_connection()` / `dict_cursor(conn)` — open connection, use `DictCursor` so rows come back as dicts
- `@admin_required` decorator wraps `@login_required` routes that need admin
- AJAX endpoints return `jsonify({success, message})`
- Call signs always `.upper()` before DB write
- `admin_comments` silently truncated to 500 chars server-side
- Record-change emails sent automatically on admin profile save (field-by-field diff)
- `VERSION` / `APP_CREDIT` constants in `app.py` flow into templates and email signatures

## Environment Variables (`.env`)

```
SECRET_KEY=
DB_HOST=db
DB_USER=
DB_PASSWORD=
DB_NAME=
DB_ROOT_PASSWORD=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
APP_URL=https://...
ORG_NAME=Your Club Name
SERVICE_DESK_URL=
LOGO_FILENAME=
ADMIN_EMAILS=
```

`ORG_NAME` flows into all page titles, navbar, email subjects/bodies, and PDF header.
`SERVICE_DESK_URL` appears in recovery/expiration emails; omit for generic "contact an administrator" text.
`LOGO_FILENAME` must exist in `static/`; omit to render org name as text.
`ADMIN_EMAILS` comma-separated list for expiration summary emails.

## Conventions

- Python: standard Flask patterns, no blueprints (single `app.py`)
- Templates: Jinja2, inherit from `base.html`; Bootstrap 5 styling
- SQL: raw parameterised queries via MySQLdb (`%s` placeholders), no ORM
- No test runner configured; `tests/test_data_setup.sql` provides manual test fixtures
- Database migrations are plain `.sql` files in `database/`
