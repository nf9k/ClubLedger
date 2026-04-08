# Membership Portal — Administrator Manual

**Version 2.3**

---

## Table of Contents

1. Introduction
2. Getting Started
3. Dashboard Overview
4. Managing Members
5. Membership Status Management
6. Exporting Data
7. Automated Expiration Notifications
8. PDF Export Feature
9. Security Best Practices
10. Troubleshooting
11. Support and Contact

---

## 1. Introduction

This guide covers all administrator functions in the Membership Portal: managing member accounts, tracking dues, handling password resets, exporting data, and monitoring automated notifications.

### 1.1 Administrator Responsibilities

* Manage member accounts and information
* Update membership status and dues records
* Handle password reset requests
* Export membership data for reporting
* Maintain data accuracy and security
* Monitor expiration notifications

---

## 2. Getting Started

### 2.1 Accessing the Portal

1. Navigate to the membership portal URL
2. Enter your call sign (uppercase, e.g., W9ABC)
3. Enter your password
4. Click **Login** to access the dashboard

### 2.2 Password Recovery

1. Click **Password Recovery** on the login page
2. Enter your registered email address
3. Click **Send Recovery Link**
4. Check your email for the reset link (valid for 24 hours)
5. Follow the link and create a new password

---

## 3. Dashboard Overview

The administrator dashboard displays all members and provides quick access to management functions.

### 3.1 Dashboard Features

* **Sortable Columns**: Click any column header to sort the member list
* **Clickable Call Signs**: Click a call sign to edit that member's profile
* **Member Count**: Total displayed at the bottom
* **Status Badges**: Colour-coded membership status (Active / Expiring / Expired)

### 3.2 Action Buttons

**Export PDF (Blue)**: Download the complete member list as a PDF

**Add Member (Green)**: Create a new member account

**Reset Password (Yellow key)**: Send a password reset email to a member

**Delete Member (Red trash)**: Remove a member from the database (requires confirmation)

---

## 4. Managing Members

### 4.1 Adding a New Member

1. Click the **Add Member** button on the dashboard
2. Complete the required fields:
   * **Call Sign** (required — used for login)
   * **Email Address** (required — password reset link is sent automatically)
   * **Name/Group Name** (required)
3. Fill in contact information (address, city, state, phone)
4. Set membership status:
   * Member Type (Full, Associate, Life, Honorary)
   * Paid Through (year, e.g., 2026)
5. **Administrator Comments** (optional) — add payment tracking notes:
   * Payment amount, date, method
   * Check numbers, PayPal confirmations
   * Renewal notes, special circumstances
   * This field is only visible to administrators
6. Check **Grant Admin Privileges** if applicable
7. Click **Add Member**

**What happens next:**
* The system automatically generates a secure random password
* The member receives an email with a password reset link (valid 24 hours)
* The member clicks the link and sets their own password
* Administrators never handle or see member passwords

**Note**: An email address is required for the automated password setup process. If a member has no email, you will need to manually assist them with password setup.

### 4.2 Editing Member Information

1. Click the member's call sign in the dashboard
2. Update any fields as needed
3. Click **Save Changes**

**Automatic notification**: When you save, the member automatically receives an email listing exactly which fields changed and the old and new values. No manual step is needed. If nothing actually changed, no email is sent.

**Administrator Comments** (admin-only field):
* Use this field to track payment information
* Record: amounts, dates, payment methods, check numbers
* Document special circumstances, board decisions
* Members cannot see this field
* 500 character limit

**Note**: Only administrators can edit call signs. If a member upgrades their licence, update their call sign here. The member will need to re-login with the new call sign.

**Administrator Comments Examples:**
```
Paid $25 via check #1234 on 02/05/2026
Renewed 2026–2027, PayPal conf XYZ123
Life membership granted 01/15/2020
Comp membership — board decision 11/2024
```

### 4.3 Changing a Call Sign

When a member upgrades or changes their licence:

1. Click the member's call sign to edit their profile
2. Update the **Call Sign** field
3. Click **Save Changes**
4. The system verifies the new call sign is not already in use
5. The member automatically receives a record change email listing the call sign update
6. If you changed your own call sign, you will be logged out and must re-login
7. If you changed another member's call sign, they must login with the new call sign

### 4.4 Resetting Member Passwords

1. Locate the member in the dashboard
2. Click the yellow key icon in the **Actions** column
3. Confirm the email address in the popup
4. The member receives an email with a reset link (valid 24 hours)

**Note**: The member must have a valid email address on file.

### 4.5 Deleting a Member

**WARNING**: Deletion is permanent and cannot be undone.

1. Locate the member in the dashboard
2. Click the red trash icon in the **Actions** column
3. Confirm the deletion in the popup dialog

**Note**: You cannot delete your own account.

---

## 5. Membership Status Management

### 5.1 Member Types

**FULL** — Regular voting member

**ASSOCIATE** — Non-voting member

**LIFE** — Lifetime member (no annual dues)

**HONORARY** — Honorary member

### 5.2 Updating Dues Status

1. Click the member's call sign to edit their profile
2. Update the **Paid Through** field with the year (e.g., 2027)
3. Update **Member Type** if needed
4. Click **Save Changes**

The member will automatically receive an email showing what changed.

### 5.3 Status Badges

**GREEN (Active)** — Paid through a future year

**YELLOW (Expiring Soon)** — Paid through the current year; needs renewal for next year

**RED (Expired)** — Paid through a past year

---

## 6. Exporting Data

### 6.1 PDF Export

1. Click the **Export PDF** button on the dashboard
2. The PDF is generated and downloaded automatically

The PDF includes:
* Organisation name and title
* Generation date/time and total member count
* Complete member table sorted by last name
* Professional formatting with alternating row colours
* Confidentiality notice

### 6.2 Automated Backups

The `scripts/backup_and_email.sh` script emails database backups to designated administrators. Each backup includes a complete SQL dump and CSV export in a compressed ZIP. Configure the recipient addresses in `.env` via `ADMIN_EMAILS`.

---

## 7. Automated Expiration Notifications

The system monitors membership expiration status and sends email notifications when a member's status changes.

### 7.1 How It Works

The notification script runs via cron and sends emails only when status actually changes:

* Status changes to **expiring** → Email: "Membership expiring soon"
* Status changes to **expired** → Email: "Membership has expired"
* Status changes to **active** → Email: "Thank you — membership is active"
* No status change → No email (prevents spam)

### 7.2 Status Definitions

**ACTIVE** — Paid through a future year

**EXPIRING** — Paid through the current year (needs renewal for next year)

**EXPIRED** — Paid through a past year

### 7.3 Administrator Summary Emails

After each automated check, administrators listed in `ADMIN_EMAILS` receive a summary containing:

* Number of notifications sent / failed
* Status changes detected (expired, expiring, renewed)
* Members notified with their status transitions
* Members without email addresses (cannot be notified automatically)
* Overall membership statistics

### 7.4 What Triggers Notifications

Notifications fire on status changes, not calendar dates:

* **January 1**: member's status moves from `expiring` (paid 2025) to `expired` → email sent
* **Admin updates paid_thru 2025 → 2027**: status moves from `expired` to `active` → email sent
* **Member stays `expiring` all year** (paid 2026): no additional emails
* **Member renews mid-year** (paid_thru updated 2026 → 2027): status moves `expiring` → `active` → email sent

### 7.5 Administrator Actions

When you receive a summary email:

1. Review failed notifications — contact members without email addresses
2. Verify expired members — confirm if renewals are pending
3. Add missing email addresses to member records when available

### 7.6 Preventing Duplicate Notifications

The database tracks `expiration_status` (last known status) and `expiration_notice_sent` (date of last notification). Emails are sent only when the current status differs from the stored status.

---

## 8. PDF Export Feature

PDF exports are useful for:
* Board meetings and reports
* Offline reference
* Record keeping and archives
* Printing hard copies

**Note**: PDF exports contain confidential member information. Store and share securely.

---

## 9. Security Best Practices

### 9.1 Password Management

* Use a strong, unique password for your admin account
* Change your password regularly (every 90 days recommended)
* Never share admin credentials
* Log out when finished, especially on shared computers

### 9.2 Data Protection

* Member data is confidential — only share with authorised individuals
* Verify member identity before making account changes
* Store downloaded backups and PDFs securely

### 9.3 Admin Account Management

* Grant admin privileges only to trusted individuals
* Review admin accounts periodically
* Remove admin access when no longer needed

---

## 10. Troubleshooting

### Cannot Login

* Verify call sign is entered in uppercase
* Use Password Recovery if needed
* Contact system administrator if problem persists

### Password Reset Email Not Received

* Check spam/junk folder
* Verify correct email address is on file
* Contact system administrator to verify SMTP configuration

### Call Sign Already in Use

* Search for an existing member with that call sign
* If a duplicate entry, delete the incorrect one
* If a member changed call signs, update the old record instead of creating a new one

### Member Cannot Login After Call Sign Change

* Verify they are using the **new** call sign
* Send a password reset if they have forgotten their password

### Expiration Notifications Not Sending

* Check that the cron job is running
* Verify SMTP settings in `.env`
* Review admin summary emails for error details
* Verify `ADMIN_EMAILS` is set in `.env`

---

## 11. Support and Contact

For technical support, refer to the project documentation or contact your system administrator.

---

73,
Membership Portal Team
