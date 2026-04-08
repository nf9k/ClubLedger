# IRC Membership Expiration Notification System

## Overview

The IRC Membership Portal now includes an automated expiration notification system that sends emails to members when their membership status changes. This prevents spam while keeping members informed about their membership status.

## How It Works

### Smart Notification Logic

The system checks membership status daily (or on your schedule) and ONLY sends emails when a member's status actually changes:

**Status Change Examples:**
- Member's dues expire → Email: "Your membership has expired"
- Member approaching expiration → Email: "Your membership expires soon"  
- Member renews → Email: "Thank you! Your membership is active"
- No status change → No email (prevents daily spam)

### Status Definitions

- **ACTIVE** - Paid through a future year (e.g., 2026 when it's 2025)
- **EXPIRING** - Paid through current year (expires Dec 31 this year)
- **EXPIRED** - Paid through a past year

### Database Tracking

Two new fields prevent duplicate notifications:
- `expiration_status` - Last known status (active/expiring/expired)
- `expiration_notice_sent` - Date notification was sent

The system compares current status vs. stored status. If different = send email and update database.

## Member Email Templates

### When Membership Expires
```
Subject: IRC Membership Expired - W9ABC

Hello W9ABC,

This is a notification that your Indiana Repeater Council membership has EXPIRED.

Your membership was paid through: 2024
Current year: 2025

To renew your membership and maintain your benefits, please contact IRC 
regarding renewal and payment options.

You can still access the membership portal to update your contact information.

For questions about your membership status or to renew:
Website: https://service-desk.ircinc.org
Email: chairman@ircinc.org

73,
Indiana Repeater Council
Membership Team
```

### When Membership Expiring Soon
```
Subject: IRC Membership Expiring Soon - W9ABC

Hello W9ABC,

This is a friendly reminder that your Indiana Repeater Council membership 
expires at the end of this year.

Your membership is paid through: 2025
Current year: 2025

To ensure uninterrupted membership, please renew before December 31, 2025.

For renewal information:
Website: https://service-desk.ircinc.org
Email: chairman@ircinc.org

73,
Indiana Repeater Council
Membership Team
```

### When Membership Renewed
```
Subject: IRC Membership Active - W9ABC

Hello W9ABC,

Thank you! Your Indiana Repeater Council membership is now ACTIVE.

Your membership is paid through: 2026

You can access the membership portal at any time.

Thank you for supporting the Indiana Repeater Council!

73,
Indiana Repeater Council
Membership Team
```

## Administrator Summary Email

After each check, administrators receive a summary of all notifications:

```
IRC Membership Expiration Notification Summary
=========================================
Date: 2026-02-05 09:00:15

Notifications Sent: 12
Failed to Send: 2

Status Changes:
- Now Expired: 5
- Expiring Soon: 3
- Renewed/Active: 4

Details:
✓ W9ABC (expiring → expired) - w9abc@email.com
✓ K9XYZ (expired → active) - k9xyz@email.com
✗ N9TEST (expiring → expired) - NO EMAIL
✓ WA9FDO (expiring → active) - wa9fdo@email.com

Total Active Members: 85
Total Expiring Soon: 8
Total Expired: 10

Members Without Email Addresses:
  • N9TEST (expired)
  • KC9ABC (expiring)

Action Required:
- Review failed notifications
- Contact members without email addresses
- Update membership records as needed
```

## Installation Steps

### 1. Copy Files to Server

Place these 4 files in `/docker/clubledger/`:
- `add_expiration_tracking.sql` - Database migration
- `check_expirations.py` - Main notification script
- `setup_expiration_notifications.sh` - Installation script
- `run_expiration_check.sh` - Cron wrapper

### 2. Run Setup

```bash
cd /docker/clubledger
chmod +x setup_expiration_notifications.sh
./setup_expiration_notifications.sh
```

This will:
- Add tracking columns to the database
- Initialize status for all current members
- Run a test check (no emails sent first time)

### 3. Add to Crontab

```bash
crontab -e
```

Add one of these lines:

**Daily at 9:00 AM:**
```
0 9 * * * /docker/clubledger/run_expiration_check.sh >> /docker/clubledger/backups/expiration_check.log 2>&1
```

**Weekly on Monday at 9:00 AM:**
```
0 9 * * 1 /docker/clubledger/run_expiration_check.sh >> /docker/clubledger/backups/expiration_check.log 2>&1
```

**First of month at 9:00 AM:**
```
0 9 1 * * /docker/clubledger/run_expiration_check.sh >> /docker/clubledger/backups/expiration_check.log 2>&1
```

## Manual Testing

To test the system manually:

```bash
cd /docker/clubledger
./run_expiration_check.sh
```

Check the output for:
- How many members were checked
- How many status changes were detected
- Which notifications were sent
- Any failures

View logs:
```bash
tail -f /docker/clubledger/backups/expiration_check.log
```

## Example Scenarios

### Scenario 1: Member's Dues Expire
```
December 2025: Status = expiring, email sent "Expiring soon"
January 2026:  Status changes to expired, email sent "Membership expired"
February 2026: Status still expired, NO EMAIL (already notified)
March 2026:    Status still expired, NO EMAIL (already notified)
```

### Scenario 2: Member Renews
```
Current:  Status = expired, already notified
Admin updates paid_thru to 2026
Next check: Status changes expired → active
Email sent: "Thank you! Membership is active"
Future checks: Status still active, NO MORE EMAILS
```

### Scenario 3: No Changes
```
Member paid through 2026 (active status)
Daily checks run, status still active
NO EMAILS SENT (prevents spam)
```

## Configuration

### Admin Email Recipients

Edit `check_expirations.py` line 32 to change who receives summaries:

```python
ADMIN_EMAILS = ['chairman@ircinc.org', 'ak9r.irc@gmail.com', 'serc1mp@sbcglobal.net']
```

### Email Templates

Email templates are in `check_expirations.py` starting at line 44.
You can customize the messages, subjects, and contact information.

### SMTP Settings

The script uses SMTP settings from your `.env` file:
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD
- SMTP_FROM_EMAIL

No additional configuration needed.

## Troubleshooting

### No Emails Being Sent

Check:
1. Is cron job running? `grep expiration /var/log/syslog`
2. Check logs: `tail /docker/clubledger/backups/expiration_check.log`
3. Verify SMTP settings in `.env`
4. Test manually: `./run_expiration_check.sh`

### Members Not Receiving Emails

Possible causes:
- Member has no email address on file (check admin summary)
- Email in spam folder (ask member to check)
- Invalid email address (admin summary will show failures)

### Duplicate Notifications

Should not happen - the system tracks status in database.
If occurring:
1. Check database: `SELECT call_sign, expiration_status, expiration_notice_sent FROM members;`
2. Verify script is not running multiple times simultaneously

### Admin Summary Not Received

Check:
1. ADMIN_EMAILS list in script is correct
2. SMTP credentials are valid
3. Check spam folder

## Database Fields

The system adds two fields to the `members` table:

```sql
expiration_notice_sent  DATE        Last date notification was sent
expiration_status       VARCHAR(20) Last known status: active, expiring, expired
```

To view current status of all members:

```bash
docker exec -it clubledger_db mariadb -u root -p
USE clubledger_db;

SELECT call_sign, paid_thru, expiration_status, expiration_notice_sent 
FROM members 
ORDER BY expiration_status, call_sign;
```

## Benefits

✅ **No Spam** - Only emails on actual status changes
✅ **Admin Visibility** - Summary shows who was notified and why
✅ **Member Friendly** - Clear, actionable messages with contact info
✅ **Tracks History** - Database records when each member was notified
✅ **Identifies Issues** - Flags members without email addresses
✅ **Renewal Confirmation** - Thanks members when they renew
✅ **Automated** - Runs without manual intervention
✅ **Safe** - Won't send duplicate emails

## Support

For questions or issues with the expiration notification system:

Website: https://service-desk.ircinc.org
Email: chairman@ircinc.org

Administrators: NF9K, AK9R, WA9FDO

---

Indiana Repeater Council
Membership Portal - Expiration Notification System
Version 2.2
