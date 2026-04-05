# ClubLedger - Changelog

---

## v1.05 (April 2026)

### FCC Lookup — Add Member
- Replaced blur-triggered badge with an inline **FCC Lookup** button on the call sign field
- Clicking immediately fetches and populates name, address, city, state, and zip
- Shows license class and active/expired status below the field

---

## v1.04 (April 2026)

### FCC Lookup — Profile Page
- Admin profile view now shows a **FCC Record** comparison card below the call sign
- Three columns: Field / Current / FCC — rows highlighted in yellow where values differ
- **Sync from FCC** button applies all FCC values at once
- Card auto-loads on page open; refreshes if call sign is changed

---

## v1.03 (April 2026)

### FCC Callsign Lookup
- New `fcc_licenses` table stores FCC ULS amateur radio license data
- `scripts/import_fcc.py` downloads and imports the full FCC dataset (~1.68M records)
- Supports `--daily` flag for incremental updates (runs via cron at 3am)
- `/admin/fcc-lookup/<callsign>` endpoint for AJAX lookups
- Download streamed to disk to avoid OOM on large FCC zip file

### Infrastructure
- `scripts/` directory now included in Docker image
- Docker image versioning introduced (`nf9k/clubledger` on Docker Hub)

---

## v1.02 (April 2026)

### Branding & Credit
- `VERSION` and `APP_CREDIT` constants added to `app.py`
- "ClubLedger vX.xx by NF9K" appears on login page, page footer, PDF footer, and email signatures
- PDF export filename now uses `ORG_NAME` instead of hardcoded "IRC_Membership_"

---

## v1.01 (April 2026)

### Project Rebranding
- Repository renamed to **ClubLedger** on GitHub
- All IRC-specific container names, paths, and references updated to `clubledger_*`
- IRC-specific documentation replaced with generic guides (Administrator Manual, Member User Guide)
- `CLAUDE.md` split: project context committed to repo; deployment-specific context stays local

### Containerised Deployment
- `Dockerfile` added — python:3.13-slim, gunicorn, baked-in app and templates
- `docker-compose.yml` added — `clubledger_web` + `clubledger_db`, static volume mount for logos
- `database/schema.sql` added — complete schema auto-applied on first MariaDB start (fresh installs skip manual migrations)

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
