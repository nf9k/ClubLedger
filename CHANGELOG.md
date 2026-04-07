# ClubLedger - Changelog

---

## v1.09 (April 2026)

### Fixed
- Removed example call sign placeholder (`W9ABC`) from login field — replaced with "Call Sign" to reduce user confusion

---

## v1.08 (April 2026)

### Added
- ZIP code lookup on profile edit and Add Member forms — auto-fills city/state on blur via `GET /zip-lookup/<zip>` (unauthenticated, queries `fcc_licenses`)
- `INDEX idx_zip (zip)` on `fcc_licenses` for fast ZIP queries
- `app/static/js/app.js` with `attachZipLookup()` helper — auto-fills if city is empty, otherwise shows clickable badge suggestions; non-destructive when city pre-filled by FCC lookup

---

## v1.07 (April 2026)

### Added
- hCaptcha on login and password recovery forms
- Widget is hidden/inactive if `HCAPTCHA_SITE_KEY` / `HCAPTCHA_SECRET_KEY` are not set — app works normally without them

### Fixed
- Hardcoded "IRC" text in password recovery form replaced with `{{ org_name }}`

---

## v1.06 (April 2026)

### Added
- Full two-factor authentication: TOTP (Google Authenticator, Authy, etc.) with QR code setup and manual key entry
- 8 backup codes in XXXX-XXXX format, bcrypt-hashed, one-time use
- WebAuthn/FIDO2 support for YubiKey and other security keys
- Login flow intercepts 2FA-enabled users and routes to challenge page before completing session
- **Security & 2FA** settings page accessible from user dropdown
- `database/add_2fa.sql` migration for existing installs
- New dependencies: `pyotp`, `qrcode[pil]`, `webauthn`

---

## v1.05 (April 2026)

### Changed
- FCC lookup on Add Member replaced blur+badge pattern with an inline **FCC Lookup** button
- Button immediately fetches and populates name, address, city, state, zip — no preview step
- Shows license class and active/expired status inline below the field

---

## v1.04 (April 2026)

### Added
- FCC comparison card on admin profile view — three columns: Field / Current / FCC
- Rows highlighted in yellow where values differ from FCC record
- **Sync from FCC** button applies all FCC values at once
- Card auto-loads on page open; refreshes if call sign is changed

---

## v1.03 (April 2026)

### Added
- `fcc_licenses` table — stores FCC ULS amateur radio license data (~1.68M records)
- `scripts/import_fcc.py` — downloads and imports full FCC dataset; `--daily` flag for incremental updates
- Daily cron at 3am for incremental FCC updates
- `/admin/fcc-lookup/<callsign>` AJAX endpoint

### Fixed
- FCC download now streams to a temp file instead of `io.BytesIO` (prevents OOM)
- `INSERT IGNORE` handles duplicate callsigns within FCC source data

### Changed
- `scripts/` directory now included in Docker image

---

## v1.02 (April 2026)

### Added
- `VERSION` and `APP_CREDIT` constants in `app.py`
- "ClubLedger vX.xx by NF9K" on login page, page footer, PDF footer, and email signatures

### Changed
- PDF export filename now uses `ORG_NAME` instead of hardcoded prefix

---

## v1.01 (April 2026)

### Added
- `Dockerfile` — python:3.13-slim, gunicorn, baked-in app and templates
- `docker-compose.yml` — `clubledger_web` + `clubledger_db`, static volume mount for logos
- `database/schema.sql` — complete schema auto-applied on first MariaDB start
- `CLAUDE.md` committed to repo (generic project context)

### Changed
- Repository renamed to **ClubLedger** on GitHub
- All IRC-specific container names and paths updated to `clubledger_*`
- IRC-specific documentation replaced with generic Administrator and Member guides
- Deployment-specific context moved to local-only `.claude/CLAUDE.md`

---

<!-- Historical entries below use the previous 2.x versioning scheme -->


## Version 2.3 (April 2026)

### New Features

#### Automatic Record Change Emails
- Members receive a field-by-field diff email whenever their record is saved
- Works for both admin edits and member self-edits
- If the email address itself changed, the notification goes to the new address
- Admin-only internal comments are never included in member-facing emails
- No email sent if nothing actually changed on the record
- Replaces the manual "Send Update Notice" button

#### Org Branding via Environment Variables
- All club-specific text is now driven by `.env` — no code changes needed
- `ORG_NAME`: flows into navbar, page titles, email subjects/bodies, PDF header
- `SERVICE_DESK_URL`: support link in emails and password recovery page; omit for generic text
- `LOGO_FILENAME`: logo image on login/recovery pages; omit to display org name as text
- `ADMIN_EMAILS`: comma-separated list for expiration summary emails; replaces hardcoded addresses

### Removed
- "Send Update Notice" dashboard button — superseded by automatic diff emails

---

## Version 2.2 (February 6, 2026)

### New Features

#### Auto-Generated Passwords
- Removed manual password entry from "Add Member" form
- System generates secure random 16-character password
- Member automatically receives password reset email
- Member sets own password via secure link
- Admins never see or handle member passwords
- Email address now required when adding members

#### Administrator Comments Field
- New admin-only field for internal notes (500 character limit)
- Track payment information: amounts, dates, methods, check numbers
- Document special circumstances and board decisions
- Members cannot see this field
- Character counter for length tracking
- Available on both Add Member and Edit Profile forms

#### PDF Export Enhancements
- Export now sorted by last name (instead of call sign)
- Professional formatting with alternating row colors
- Landscape orientation for better readability
- Includes generation timestamp and member count
- Confidentiality notice footer

#### Call Sign Management
- Admins can now change member call signs
- Duplicate call sign validation
- Automatic logout when member's call sign changes
- System prompts for re-login with new call sign
- Regular members cannot change own call sign

#### Automated Expiration Notifications
- Email notifications sent when membership status changes
- Three status levels: Active, Expiring, Expired
- Smart logic prevents duplicate notifications
- Admin summary emails after each check run
- Tracks notification history in database
- Cron-compatible for scheduled execution

#### Update Notifications
- Admins can manually notify members of record updates
- "Send Update Notice" button on dashboard
- Email includes portal link and contact information
- Cannot send to self
- Only sends if member has email address

### User Interface Improvements

#### Dashboard Enhancements
- Sortable columns (click headers to sort)
- Call signs are clickable links to edit profiles
- Color-coded status badges (Green/Yellow/Red)
- Action buttons for each member:
  - Send Update Notice (envelope icon)
  - Reset Password (key icon)
  - Delete Member (trash icon)
- Member count displayed at bottom

#### Profile Editor Updates
- Call sign field editable by admins only
- Admin comments section for administrators
- Character counter on comment fields
- Improved field organization and labels
- Better visual distinction of admin-only fields

### Bug Fixes
- Fixed admin status preservation when editing own profile
- Corrected status badge logic for current year memberships
- Fixed member type field not being editable
- Resolved issue with dashboard not showing all features after updates
- Improved error handling for missing email addresses

### Database Changes
- Added `admin_comments` field (TEXT, 500 char limit)
- Added `expiration_status` field (VARCHAR(20))
- Added `expiration_notice_sent` field (DATE)
- No breaking changes to existing data

### Security Enhancements
- Removed admin password visibility
- Added duplicate call sign validation
- Improved session handling for call sign changes
- Enhanced input validation and sanitization
- Better authorization checks on admin-only routes

### Documentation
- Complete Administrator Manual v2.2
- Updated Member User Guide v2.2
- Comprehensive Test Plan (90+ test cases)
- Expiration Notification System guide
- Deployment procedures

---

## Version 2.1 (December 2024)

### Features
- Initial membership portal with dashboard
- Basic member CRUD operations
- Password recovery via email
- Status badges (Active/Expiring/Expired)
- Admin privilege management
- Member type field (Full/Associate/Life/Honorary)

---

## Version 2.0 (December 2024)

### Features
- Initial release
- Docker containerization
- Flask web application
- MariaDB database
- User authentication
- Basic profile management

---

## Migration Notes

### From v2.1 to v2.2
1. Database migrations required (add_admin_comments.sql)
2. New Python dependencies (existing ones compatible)
3. Template updates (all templates modified)
4. New scripts added (expiration checks, backups)
5. No data loss - all existing data preserved
6. Member passwords remain unchanged
7. Requires brief downtime for container rebuild

### Backward Compatibility
- All v2.1 data fully compatible
- Existing member accounts work without changes
- Admin privileges preserved
- Sessions may need refresh after deployment
- Bookmarks to old URLs remain valid

---

## Known Issues

### v2.2
- PDF export performance degrades beyond ~1000 members
- Session timeout fixed at 24 hours (not configurable via UI)
- Email delivery depends on SMTP provider reliability
- Expiration notifications require cron setup (not automatic)

### Planned for Future Releases
- Multi-language support
- Mobile app
- API for external integrations
- Advanced reporting and analytics
- Bulk import/export tools
- Member self-registration workflow
