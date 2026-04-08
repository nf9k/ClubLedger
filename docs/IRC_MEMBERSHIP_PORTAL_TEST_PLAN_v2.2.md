# Indiana Repeater Council Membership Portal
# Test Plan - Version 2.2

**Document Version:** 1.0  
**Last Updated:** February 5, 2026  
**System Version:** 2.2

---

## Table of Contents

1. Introduction
2. Test Environment Setup
3. Pre-Test Data Preparation
4. Authentication & Security Tests
5. Member Management Tests
6. Profile Management Tests
7. Admin Features Tests
8. Status & Notification Tests
9. Export & Reporting Tests
10. Edge Cases & Error Handling
11. Performance Tests
12. Regression Test Checklist
13. Sign-Off

---

## 1. Introduction

### 1.1 Purpose
This test plan provides comprehensive testing procedures for the IRC Membership Portal to ensure all features work correctly before deployment to production.

### 1.2 Scope
This plan covers:
- User authentication (login, logout, password recovery)
- Member CRUD operations (Create, Read, Update, Delete)
- Admin-specific features
- Status badge logic
- Expiration notifications
- PDF exports
- Email functionality
- Data validation
- Security controls

### 1.3 Test Levels
- **Unit Testing**: Individual component validation
- **Integration Testing**: Multi-component workflows
- **System Testing**: End-to-end scenarios
- **Regression Testing**: Verify existing features still work after changes

### 1.4 Test Environment Requirements
- Docker containers running (clubledger_db, clubledger_web)
- Valid .env configuration
- Test email account accessible
- Sample member data loaded
- Admin account credentials available

---

## 2. Test Environment Setup

### 2.1 Prerequisites Checklist
```
☐ Docker Compose running (docker compose ps shows healthy containers)
☐ Database accessible (docker exec clubledger_db mariadb -u root -p)
☐ Web interface accessible (http://[host]:5000)
☐ SMTP credentials configured in .env
☐ Test email account monitored (for receiving emails)
☐ Browser with dev tools available
☐ Database backup created before testing
```

### 2.2 Test Data Setup

Create test accounts:
```sql
-- Run in database before testing
USE clubledger_db;

-- Test admin account
INSERT INTO members (call_sign, password_hash, email, name, paid_thru, member_type, is_admin)
VALUES ('TEST1ADM', '[hashed_password]', 'testadmin@test.com', 'Test Admin', '2027', 'FULL', 1);

-- Test regular member (active)
INSERT INTO members (call_sign, password_hash, email, name, paid_thru, member_type, is_admin)
VALUES ('TEST2MEM', '[hashed_password]', 'testmember@test.com', 'Test Member Active', '2027', 'FULL', 0);

-- Test expiring member
INSERT INTO members (call_sign, password_hash, email, name, paid_thru, member_type, is_admin)
VALUES ('TEST3EXP', '[hashed_password]', 'testexpiring@test.com', 'Test Member Expiring', '2026', 'FULL', 0);

-- Test expired member
INSERT INTO members (call_sign, password_hash, email, name, paid_thru, member_type, is_admin)
VALUES ('TEST4OLD', '[hashed_password]', 'testexpired@test.com', 'Test Member Expired', '2025', 'ASSOCIATE', 0);

-- Test member without email
INSERT INTO members (call_sign, password_hash, name, paid_thru, member_type, is_admin)
VALUES ('TEST5NOE', '[hashed_password]', 'Test No Email', '2027', 'LIFE', 0);
```

---

## 3. Pre-Test Data Preparation

### 3.1 Verify Database Schema
```sql
-- Check all required fields exist
DESCRIBE members;

-- Verify these columns exist:
-- id, call_sign, password_hash, email, name, primary_rep, rep_call,
-- address, city, state, zip, telephone, paid_thru, member_type,
-- is_admin, admin_comments, expiration_status, expiration_notice_sent,
-- created_at, updated_at
```

### 3.2 Verify File Structure
```
☐ app/app.py exists
☐ app/templates/*.html all exist
☐ .env contains all required variables
☐ check_expirations.py exists
☐ backup scripts exist
```

---

## 4. Authentication & Security Tests

### 4.1 Login - Valid Credentials

**Test ID:** AUTH-001  
**Priority:** Critical

**Steps:**
1. Navigate to portal login page
2. Enter valid call sign (uppercase): TEST1ADM
3. Enter correct password
4. Click "Login"

**Expected Results:**
- ✓ Redirects to dashboard
- ✓ Session cookie created
- ✓ User sees member list (if admin) or own profile (if member)
- ✓ Logout link visible in header

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.2 Login - Invalid Password

**Test ID:** AUTH-002  
**Priority:** Critical

**Steps:**
1. Navigate to login page
2. Enter valid call sign: TEST1ADM
3. Enter incorrect password
4. Click "Login"

**Expected Results:**
- ✓ Stays on login page
- ✓ Error message displayed: "Invalid call sign or password"
- ✓ No session created
- ✓ Password field cleared

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.3 Login - Non-Existent User

**Test ID:** AUTH-003  
**Priority:** High

**Steps:**
1. Navigate to login page
2. Enter non-existent call sign: FAKE123
3. Enter any password
4. Click "Login"

**Expected Results:**
- ✓ Stays on login page
- ✓ Error message: "Invalid call sign or password"
- ✓ No information leaked about whether user exists

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.4 Login - Case Sensitivity

**Test ID:** AUTH-004  
**Priority:** Medium

**Steps:**
1. Navigate to login page
2. Enter call sign in lowercase: test1adm
3. Enter correct password
4. Click "Login"

**Expected Results:**
- ✓ Login succeeds (call signs should be case-insensitive)
- ✓ System internally converts to uppercase

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.5 Password Recovery - Valid Email

**Test ID:** AUTH-005  
**Priority:** Critical

**Steps:**
1. Navigate to login page
2. Click "Password Recovery"
3. Enter valid email: testadmin@test.com
4. Click "Send Recovery Link"
5. Check email inbox

**Expected Results:**
- ✓ Success message: "Password reset email sent"
- ✓ Email received within 2 minutes
- ✓ Email contains reset link
- ✓ Link is valid (not expired)
- ✓ Link format: /reset-password/[token]

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.6 Password Recovery - Invalid Email

**Test ID:** AUTH-006  
**Priority:** Medium

**Steps:**
1. Navigate to Password Recovery page
2. Enter email not in system: fake@test.com
3. Click "Send Recovery Link"

**Expected Results:**
- ✓ Success message shown (don't leak info about valid emails)
- ✓ No email sent
- ✓ No error logged in application

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.7 Password Reset - Valid Token

**Test ID:** AUTH-007  
**Priority:** Critical

**Steps:**
1. Complete AUTH-005 to get reset link
2. Click link from email
3. Enter new password: TestPass123!
4. Confirm password: TestPass123!
5. Click "Reset Password"
6. Login with new password

**Expected Results:**
- ✓ Redirects to reset page with token
- ✓ Password fields visible
- ✓ Success message after reset
- ✓ Can login with new password
- ✓ Old password no longer works

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.8 Password Reset - Expired Token

**Test ID:** AUTH-008  
**Priority:** Medium

**Steps:**
1. Generate password reset link
2. Wait 25 hours (or manually expire in database)
3. Click expired link

**Expected Results:**
- ✓ Error message: "Reset link expired"
- ✓ Option to request new link
- ✓ Cannot reset password with old token

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.9 Session Management - Logout

**Test ID:** AUTH-009  
**Priority:** High

**Steps:**
1. Login as TEST1ADM
2. Navigate to dashboard
3. Click "Logout" link
4. Verify logout
5. Try to access dashboard directly

**Expected Results:**
- ✓ Redirects to login page
- ✓ Session cookie deleted
- ✓ Cannot access protected pages
- ✓ Attempting to access /dashboard redirects to login

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.10 Session Management - Timeout

**Test ID:** AUTH-010  
**Priority:** Medium

**Steps:**
1. Login as TEST1ADM
2. Wait 24 hours (or manually expire session)
3. Try to perform action

**Expected Results:**
- ✓ Session expires after 24 hours
- ✓ Redirects to login
- ✓ Must re-authenticate

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.11 Authorization - Admin-Only Access

**Test ID:** AUTH-011  
**Priority:** Critical

**Steps:**
1. Login as regular member (TEST2MEM)
2. Try to access admin URLs:
   - /admin/add-member
   - /profile/[other_user_id]
   - /admin/delete-member/[id]
   - /admin/export-pdf

**Expected Results:**
- ✓ Access denied / redirected
- ✓ Error message: "Admin access required"
- ✓ No data leaked

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 4.12 Authorization - Self-Profile Only

**Test ID:** AUTH-012  
**Priority:** High

**Steps:**
1. Login as TEST2MEM (user_id = X)
2. Try to access /profile/[different_user_id]

**Expected Results:**
- ✓ Access denied
- ✓ Error: "You do not have permission"
- ✓ Can only access own profile (/profile/X)

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 5. Member Management Tests

### 5.1 Add Member - Complete Valid Data

**Test ID:** MEMBER-001  
**Priority:** Critical

**Steps:**
1. Login as admin (TEST1ADM)
2. Click "Add Member"
3. Fill all fields:
   - Call Sign: NEWADD1
   - Email: newadd1@test.com
   - Name: New Member Test
   - Address: 123 Test St
   - City: Indianapolis
   - State: IN
   - ZIP: 46220
   - Telephone: 317-555-1234
   - Member Type: FULL
   - Paid Through: 2027
   - Admin Comments: "Test member - paid $25 check #999"
4. Check "Grant Admin Privileges" (leave unchecked)
5. Click "Add Member"

**Expected Results:**
- ✓ Success message: "Member NEWADD1 added successfully! Password reset email sent..."
- ✓ Redirects to dashboard
- ✓ Member visible in member list
- ✓ Email sent to newadd1@test.com with password reset link
- ✓ Admin comments saved but not visible to member
- ✓ Random password generated (not visible to admin)

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.2 Add Member - Duplicate Call Sign

**Test ID:** MEMBER-002  
**Priority:** High

**Steps:**
1. Login as admin
2. Click "Add Member"
3. Enter call sign that already exists: TEST1ADM
4. Fill other required fields
5. Click "Add Member"

**Expected Results:**
- ✓ Error message: "Call sign or email already exists"
- ✓ Member not added
- ✓ Form retains entered data
- ✓ Database unchanged

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.3 Add Member - Duplicate Email

**Test ID:** MEMBER-003  
**Priority:** High

**Steps:**
1. Login as admin
2. Click "Add Member"
3. Enter unique call sign but duplicate email: testadmin@test.com
4. Fill other fields
5. Click "Add Member"

**Expected Results:**
- ✓ Error message: "Call sign or email already exists"
- ✓ Member not added

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.4 Add Member - Missing Required Fields

**Test ID:** MEMBER-004  
**Priority:** Medium

**Steps:**
1. Login as admin
2. Click "Add Member"
3. Leave Call Sign empty
4. Fill email and name
5. Try to submit

**Expected Results:**
- ✓ Browser validation prevents submit
- ✓ Required field highlighted
- ✓ Error message shown

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.5 Add Member - Without Email

**Test ID:** MEMBER-005  
**Priority:** Medium

**Steps:**
1. Login as admin
2. Click "Add Member"
3. Fill call sign and name
4. Leave email blank
5. Submit

**Expected Results:**
- ✓ Warning message: "Member added, but no email provided"
- ✓ Member created in database
- ✓ No password reset email sent
- ✓ Admin must manually assist member with password

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.6 Add Member - Admin Comments Character Limit

**Test ID:** MEMBER-006  
**Priority:** Low

**Steps:**
1. Login as admin
2. Click "Add Member"
3. Fill required fields
4. In Admin Comments, paste 600 characters of text
5. Submit

**Expected Results:**
- ✓ Character counter shows 500/500
- ✓ Only first 500 characters saved
- ✓ Form prevents entry beyond 500 chars OR truncates

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.7 View Member List - Admin View

**Test ID:** MEMBER-007  
**Priority:** High

**Steps:**
1. Login as admin (TEST1ADM)
2. View dashboard

**Expected Results:**
- ✓ All members visible
- ✓ Sortable columns (click header to sort)
- ✓ Status badges show correct colors:
  - Green for paid 2027+
  - Yellow for paid 2026
  - Red for paid 2025-
- ✓ Action buttons visible for each member:
  - Send Update Notice (envelope)
  - Reset Password (key)
  - Delete (trash)
- ✓ Call signs are blue clickable links

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.8 View Member List - Regular Member View

**Test ID:** MEMBER-008  
**Priority:** High

**Steps:**
1. Login as regular member (TEST2MEM)
2. View dashboard

**Expected Results:**
- ✓ Only sees own profile
- ✓ No action buttons visible
- ✓ Cannot see other members
- ✓ "My Profile" heading instead of "Member Management"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.9 Delete Member - Confirmation Required

**Test ID:** MEMBER-009  
**Priority:** Critical

**Steps:**
1. Login as admin
2. Navigate to dashboard
3. Click delete (trash icon) for TEST4OLD
4. Observe confirmation dialog
5. Click "Cancel"
6. Verify member still exists

**Expected Results:**
- ✓ Confirmation dialog appears
- ✓ Dialog warns: "Are you sure? This cannot be undone"
- ✓ Cancel button prevents deletion
- ✓ Member still in database

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.10 Delete Member - Successful Deletion

**Test ID:** MEMBER-010  
**Priority:** High

**Steps:**
1. Login as admin
2. Navigate to dashboard
3. Click delete for TEST4OLD
4. Confirm deletion
5. Verify removal

**Expected Results:**
- ✓ Confirmation dialog appears
- ✓ Click "Confirm"
- ✓ Success message: "Member deleted"
- ✓ Member removed from list
- ✓ Database record deleted
- ✓ Cannot login with deleted account

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 5.11 Delete Member - Cannot Delete Self

**Test ID:** MEMBER-011  
**Priority:** High

**Steps:**
1. Login as admin (TEST1ADM)
2. Navigate to dashboard
3. Attempt to delete own account

**Expected Results:**
- ✓ Delete button not visible for own account
- ✓ If manually accessed via URL: Error message
- ✓ "You cannot delete your own account"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 6. Profile Management Tests

### 6.1 Edit Own Profile - Regular Member

**Test ID:** PROFILE-001  
**Priority:** High

**Steps:**
1. Login as TEST2MEM
2. View profile
3. Update editable fields:
   - Email: newemail@test.com
   - Address: 456 New St
   - City: Carmel
   - Telephone: 317-555-9999
4. Click "Save Changes"

**Expected Results:**
- ✓ Success message: "Profile updated"
- ✓ Changes saved in database
- ✓ Cannot edit:
  - Call Sign (disabled/grayed)
  - Member Type (disabled)
  - Paid Through (disabled)
  - Admin Comments (not visible)

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.2 Edit Own Profile - Admin Cannot Demote Self

**Test ID:** PROFILE-002  
**Priority:** Critical

**Steps:**
1. Login as admin (TEST1ADM)
2. Edit own profile
3. Uncheck "Grant Admin Privileges"
4. Save

**Expected Results:**
- ✓ Admin checkbox should not be changeable for own profile
- ✓ OR if changeable, saving preserves admin status
- ✓ Cannot accidentally demote self

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.3 Edit Other Member - Admin Full Access

**Test ID:** PROFILE-003  
**Priority:** High

**Steps:**
1. Login as admin (TEST1ADM)
2. Click TEST2MEM call sign
3. Update all fields including:
   - Member Type: ASSOCIATE
   - Paid Through: 2028
   - Admin Comments: "Updated by admin"
4. Check "Grant Admin Privileges"
5. Save

**Expected Results:**
- ✓ All fields editable by admin
- ✓ Changes saved
- ✓ Member Type updated
- ✓ Paid Through updated
- ✓ Admin status granted
- ✓ Admin Comments saved

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.4 Change Call Sign - Admin Only

**Test ID:** PROFILE-004  
**Priority:** High

**Steps:**
1. Login as admin
2. Edit TEST3EXP
3. Change call sign from TEST3EXP to TEST3NEW
4. Save

**Expected Results:**
- ✓ Call sign updated in database
- ✓ Member can login with TEST3NEW
- ✓ Cannot login with TEST3EXP anymore
- ✓ If member logged in, they're logged out
- ✓ Flash message: "Call sign updated, member must re-login"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.5 Change Call Sign - Duplicate Prevention

**Test ID:** PROFILE-005  
**Priority:** High

**Steps:**
1. Login as admin
2. Edit TEST2MEM
3. Try to change call sign to TEST1ADM (existing)
4. Save

**Expected Results:**
- ✓ Error message: "Call sign TEST1ADM is already in use"
- ✓ Change not saved
- ✓ Original call sign preserved

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.6 Change Call Sign - Self (Admin)

**Test ID:** PROFILE-006  
**Priority:** Medium

**Steps:**
1. Login as TEST1ADM
2. Edit own profile
3. Change call sign from TEST1ADM to TEST1NEW
4. Save

**Expected Results:**
- ✓ Call sign updated
- ✓ Immediately logged out
- ✓ Flash: "Call sign updated to TEST1NEW. Please login with new call sign"
- ✓ Must re-login with TEST1NEW

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.7 Change Password - Valid Current Password

**Test ID:** PROFILE-007  
**Priority:** High

**Steps:**
1. Login as TEST2MEM
2. Scroll to Security section
3. Click "Change Password"
4. Enter current password
5. Enter new password: NewPass123!
6. Confirm new password: NewPass123!
7. Click "Update Password"

**Expected Results:**
- ✓ Success message: "Password updated"
- ✓ Can logout and re-login with new password
- ✓ Old password no longer works

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.8 Change Password - Wrong Current Password

**Test ID:** PROFILE-008  
**Priority:** Medium

**Steps:**
1. Login as TEST2MEM
2. Try to change password
3. Enter incorrect current password
4. Enter new password
5. Submit

**Expected Results:**
- ✓ Error: "Current password incorrect"
- ✓ Password not changed
- ✓ Can still login with original password

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.9 Change Password - Mismatch Confirmation

**Test ID:** PROFILE-009  
**Priority:** Low

**Steps:**
1. Login as TEST2MEM
2. Change password form
3. Enter correct current password
4. New password: Test123!
5. Confirm password: Test456! (different)
6. Submit

**Expected Results:**
- ✓ Error: "Passwords do not match"
- ✓ Password not changed

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 6.10 Admin Comments - Visibility Test

**Test ID:** PROFILE-010  
**Priority:** High

**Steps:**
1. Login as admin
2. Edit TEST2MEM profile
3. Add admin comment: "Paid $25 on 02/05/26"
4. Save
5. Logout
6. Login as TEST2MEM
7. View own profile

**Expected Results:**
- ✓ Admin can see and edit comments field
- ✓ Regular member CANNOT see admin comments field
- ✓ Comments saved in database
- ✓ Field label clearly says "Admin Only"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 7. Admin Features Tests

### 7.1 Send Update Notification - Valid Member

**Test ID:** ADMIN-001  
**Priority:** High

**Steps:**
1. Login as admin
2. Dashboard view
3. Click envelope icon for TEST2MEM
4. Confirm sending
5. Check member's email

**Expected Results:**
- ✓ Confirmation dialog appears
- ✓ Success message after sending
- ✓ Email received within 2 minutes
- ✓ Subject: "Your Indiana Repeater Council membership record has been updated"
- ✓ Contains link to portal

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.2 Send Update Notification - No Email

**Test ID:** ADMIN-002  
**Priority:** Medium

**Steps:**
1. Login as admin
2. Try to send update notice to TEST5NOE (no email)

**Expected Results:**
- ✓ Button not visible OR
- ✓ Error message: "Member has no email address"
- ✓ No email sent

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.3 Send Update Notification - Cannot Send to Self

**Test ID:** ADMIN-003  
**Priority:** Low

**Steps:**
1. Login as admin (TEST1ADM)
2. View dashboard
3. Find own entry

**Expected Results:**
- ✓ Envelope button not visible for own account
- ✓ Cannot send update notice to self

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.4 Reset Password (Admin Initiated) - Valid Email

**Test ID:** ADMIN-004  
**Priority:** High

**Steps:**
1. Login as admin
2. Click key icon for TEST2MEM
3. Confirm email address
4. Send reset
5. Check member's email

**Expected Results:**
- ✓ Confirmation dialog shows email address
- ✓ Success message
- ✓ Password reset email sent to member
- ✓ Member can use link to reset password

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.5 Reset Password (Admin Initiated) - No Email

**Test ID:** ADMIN-005  
**Priority:** Medium

**Steps:**
1. Login as admin
2. Try to reset password for TEST5NOE (no email)

**Expected Results:**
- ✓ Button not visible OR
- ✓ Error: "Member has no email address"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.6 Sortable Columns - Click to Sort

**Test ID:** ADMIN-006  
**Priority:** Medium

**Steps:**
1. Login as admin
2. View dashboard with multiple members
3. Click "Call Sign" column header
4. Click "Name" column header
5. Click "Paid Through" column header

**Expected Results:**
- ✓ Clicking header sorts ascending
- ✓ Clicking again sorts descending
- ✓ Visual indicator (arrow) shows sort direction
- ✓ All columns sortable

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 7.7 Clickable Call Signs

**Test ID:** ADMIN-007  
**Priority:** Medium

**Steps:**
1. Login as admin
2. View dashboard
3. Click on any call sign (blue link)

**Expected Results:**
- ✓ Call signs displayed as blue clickable links
- ✓ Clicking opens profile edit page
- ✓ Correct member profile loads

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 8. Status & Notification Tests

### 8.1 Status Badge - Active (Green)

**Test ID:** STATUS-001  
**Priority:** High

**Steps:**
1. Login as admin
2. View member with paid_thru = 2027 (future year)

**Expected Results:**
- ✓ Status badge shows "Active"
- ✓ Badge color is GREEN
- ✓ Tooltip or text: "Paid through 2027"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.2 Status Badge - Expiring (Yellow)

**Test ID:** STATUS-002  
**Priority:** High

**Steps:**
1. Login as admin
2. View member with paid_thru = 2026 (current year)

**Expected Results:**
- ✓ Status badge shows "Expiring"
- ✓ Badge color is YELLOW
- ✓ Shows all year (not just Nov/Dec)

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.3 Status Badge - Expired (Red)

**Test ID:** STATUS-003  
**Priority:** High

**Steps:**
1. Login as admin
2. View member with paid_thru = 2025 (past year)

**Expected Results:**
- ✓ Status badge shows "Expired"
- ✓ Badge color is RED

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.4 Status Calculation - Boundary Test

**Test ID:** STATUS-004  
**Priority:** Medium

**Steps:**
1. Create test member with paid_thru = current year
2. Verify status is "Expiring" (yellow)
3. Update paid_thru = current year + 1
4. Verify status changes to "Active" (green)
5. Update paid_thru = current year - 1
6. Verify status changes to "Expired" (red)

**Expected Results:**
- ✓ Status updates immediately after paid_thru change
- ✓ Correct color coding
- ✓ Database expiration_status field updates

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.5 Expiration Notification - Manual Test Run

**Test ID:** NOTIFY-001  
**Priority:** High

**Steps:**
1. SSH to server
2. Run: `./run_expiration_check.sh`
3. Monitor console output
4. Check admin email

**Expected Results:**
- ✓ Script runs without errors
- ✓ Console shows member count
- ✓ Shows status changes detected
- ✓ Admin summary email received
- ✓ Email contains:
  - Total notifications sent
  - Status changes breakdown
  - Failed notifications (if any)
  - Members without email

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.6 Expiration Notification - Status Change Detection

**Test ID:** NOTIFY-002  
**Priority:** High

**Steps:**
1. Check TEST3EXP current status in database
2. Update paid_thru to trigger status change
3. Run notification script
4. Check member's email

**Expected Results:**
- ✓ Status change detected
- ✓ Notification email sent to member
- ✓ expiration_status updated in database
- ✓ expiration_notice_sent date set to today
- ✓ Admin receives summary

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.7 Expiration Notification - No Duplicate Sends

**Test ID:** NOTIFY-003  
**Priority:** High

**Steps:**
1. Run notification script first time
2. Note which members notified
3. Run script again immediately (no changes)
4. Check email

**Expected Results:**
- ✓ First run: Notifications sent
- ✓ Second run: No notifications sent
- ✓ Message: "No status changes detected"
- ✓ Members don't receive duplicate emails

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.8 Expiration Notification - Member Without Email

**Test ID:** NOTIFY-004  
**Priority:** Medium

**Steps:**
1. Ensure TEST5NOE has no email
2. Change paid_thru to trigger status change
3. Run notification script
4. Check admin summary

**Expected Results:**
- ✓ Status change detected
- ✓ NO email sent (no email address)
- ✓ Logged in admin summary as "failed"
- ✓ Reason: "NO EMAIL"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 8.9 Expiration Notification - Email Content

**Test ID:** NOTIFY-005  
**Priority:** Medium

**Steps:**
1. Trigger expiration notification
2. Check member email content

**Expected Results:**
- ✓ Subject line appropriate for status
- ✓ Body contains:
  - Member's call sign
  - Current paid through year
  - Clear action needed
  - Link to portal
  - Contact information
- ✓ Professional formatting
- ✓ IRC branding/signature

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 9. Export & Reporting Tests

### 9.1 PDF Export - Generate Report

**Test ID:** EXPORT-001  
**Priority:** High

**Steps:**
1. Login as admin
2. Click "Export PDF" button
3. Wait for download
4. Open PDF

**Expected Results:**
- ✓ PDF downloads automatically
- ✓ Filename: {ORG_NAME}_Membership_YYYYMMDD_HHMM.pdf
- ✓ Opens without errors
- ✓ Contains all members

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 9.2 PDF Export - Content Validation

**Test ID:** EXPORT-002  
**Priority:** High

**Steps:**
1. Generate PDF export
2. Review contents

**Expected Results:**
- ✓ Header: "Indiana Repeater Council Membership Database"
- ✓ Generation date and time
- ✓ Total member count
- ✓ Table with columns:
  - Call Sign, Name, Email, City, State
  - Member Type, Paid Through, Admin
- ✓ All rows populated
- ✓ Professional formatting
- ✓ Landscape orientation
- ✓ Alternating row colors
- ✓ Footer: Confidentiality notice

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 9.3 PDF Export - Sort Order

**Test ID:** EXPORT-003  
**Priority:** Medium

**Steps:**
1. Generate PDF export
2. Check member order

**Expected Results:**
- ✓ Members sorted by LAST NAME (not call sign)
- ✓ Alphabetical A-Z
- ✓ Example: "John Smith" before "Mary Wilson"

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 9.4 PDF Export - Large Dataset

**Test ID:** EXPORT-004  
**Priority:** Low

**Steps:**
1. Add 100+ test members
2. Generate PDF export
3. Review

**Expected Results:**
- ✓ All members included
- ✓ Multiple pages if needed
- ✓ Page numbers visible
- ✓ Headers repeat on each page
- ✓ No truncation

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 9.5 PDF Export - Non-Admin Cannot Access

**Test ID:** EXPORT-005  
**Priority:** Medium

**Steps:**
1. Login as regular member
2. Try to access /admin/export-pdf directly

**Expected Results:**
- ✓ Access denied
- ✓ Redirected or error message
- ✓ PDF not generated

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 9.6 Database Backup - Automated Email

**Test ID:** EXPORT-006  
**Priority:** Medium

**Steps:**
1. Run backup script: `./backup_and_email.sh`
2. Check admin emails

**Expected Results:**
- ✓ Backup creates ZIP file
- ✓ ZIP contains:
  - SQL dump
  - CSV export
- ✓ Email sent to all admin addresses
- ✓ Email has ZIP attached
- ✓ Email body contains:
  - Backup date/time
  - Member count
  - Restore instructions

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 10. Edge Cases & Error Handling

### 10.1 SQL Injection - Login Form

**Test ID:** EDGE-001  
**Priority:** Critical

**Steps:**
1. Try to login with:
   - Call sign: ' OR '1'='1
   - Password: anything
2. Try other SQL injection patterns

**Expected Results:**
- ✓ Login fails
- ✓ No SQL error messages
- ✓ No unauthorized access
- ✓ Queries properly parameterized

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.2 XSS - Name Field

**Test ID:** EDGE-002  
**Priority:** High

**Steps:**
1. Login as admin
2. Add member with name: `<script>alert('XSS')</script>`
3. View dashboard

**Expected Results:**
- ✓ Script not executed
- ✓ Name displayed as plain text
- ✓ HTML escaped properly
- ✓ No alert popup

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.3 XSS - Admin Comments

**Test ID:** EDGE-003  
**Priority:** High

**Steps:**
1. Add member
2. In admin comments: `<script>alert('test')</script>`
3. View profile

**Expected Results:**
- ✓ Script not executed
- ✓ Comments displayed as plain text
- ✓ Proper escaping

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.4 Long Input Strings - Call Sign

**Test ID:** EDGE-004  
**Priority:** Low

**Steps:**
1. Try to add member with 100-character call sign
2. Try to add member with special characters: `TEST@#$%`

**Expected Results:**
- ✓ Reasonable length limit enforced
- ✓ Invalid characters rejected or sanitized
- ✓ Helpful error message

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.5 Database Connection Loss

**Test ID:** EDGE-005  
**Priority:** Medium

**Steps:**
1. Stop database container: `docker stop clubledger_db`
2. Try to access portal
3. Restart database

**Expected Results:**
- ✓ Graceful error message
- ✓ No stack trace exposed
- ✓ "Database unavailable" message
- ✓ Recovers when DB restarted

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.6 SMTP Failure - Add Member

**Test ID:** EDGE-006  
**Priority:** Medium

**Steps:**
1. Temporarily misconfigure SMTP in .env
2. Try to add new member with email
3. Check result

**Expected Results:**
- ✓ Member added to database
- ✓ Warning message: "Member added but failed to send email"
- ✓ Admin can manually send reset later

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.7 Concurrent Edits

**Test ID:** EDGE-007  
**Priority:** Low

**Steps:**
1. Login as admin in two browsers
2. Edit same member in both
3. Save from browser 1
4. Save from browser 2

**Expected Results:**
- ✓ Last write wins (acceptable)
- ✓ No database corruption
- ✓ Both saves complete

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.8 Browser Back Button

**Test ID:** EDGE-008  
**Priority:** Low

**Steps:**
1. Login
2. Navigate through pages
3. Click browser back button multiple times
4. Try to perform actions

**Expected Results:**
- ✓ Session still valid
- ✓ Pages reload properly
- ✓ No stale data shown
- ✓ CSRF tokens still valid

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.9 Special Characters - All Fields

**Test ID:** EDGE-009  
**Priority:** Medium

**Steps:**
1. Create member with special chars in all fields:
   - Name: O'Brien-Smith Jr.
   - Address: 123½ Main St. Apt #5
   - City: Saint-François
   - Email: test+tag@domain.co.uk

**Expected Results:**
- ✓ All special characters accepted
- ✓ Saved correctly
- ✓ Display correctly
- ✓ No encoding issues

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 10.10 Empty/Null Values

**Test ID:** EDGE-010  
**Priority:** Medium

**Steps:**
1. Edit member
2. Clear optional fields (address, phone, etc.)
3. Save

**Expected Results:**
- ✓ Optional fields can be empty
- ✓ No errors on NULL values
- ✓ Display handles empty fields gracefully

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 11. Performance Tests

### 11.1 Dashboard Load Time - 100 Members

**Test ID:** PERF-001  
**Priority:** Medium

**Steps:**
1. Ensure database has ~100 members
2. Clear browser cache
3. Login as admin
4. Time dashboard load

**Expected Results:**
- ✓ Page loads in < 2 seconds
- ✓ No lag scrolling
- ✓ All data visible

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 11.2 PDF Generation Time

**Test ID:** PERF-002  
**Priority:** Low

**Steps:**
1. Login as admin
2. Time PDF export for 100+ members

**Expected Results:**
- ✓ PDF generates in < 5 seconds
- ✓ Download starts immediately

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

### 11.3 Database Query Performance

**Test ID:** PERF-003  
**Priority:** Low

**Steps:**
1. SSH to server
2. Run: `./check_expirations.py`
3. Monitor execution time

**Expected Results:**
- ✓ Script completes in < 30 seconds for 100 members
- ✓ No timeout errors

**Status:** ☐ Pass ☐ Fail ☐ Blocked

---

## 12. Regression Test Checklist

After any code changes, run this quick checklist:

```
☐ Login works (admin and regular)
☐ Add member works (with auto-password)
☐ Edit member works
☐ Delete member works (with confirmation)
☐ Status badges show correct colors
☐ PDF export works and sorts by last name
☐ Admin comments visible to admins only
☐ Password reset emails send
☐ Update notifications send
☐ Expiration script runs without errors
☐ All links in navigation work
☐ Logout works properly
☐ Non-admins cannot access admin features
```

---

## 13. Sign-Off

### Test Summary

**Total Test Cases:** ___  
**Passed:** ___  
**Failed:** ___  
**Blocked:** ___  
**Not Tested:** ___

### Critical Issues Found

| Issue ID | Description | Severity | Status |
|----------|-------------|----------|--------|
|          |             |          |        |

### Recommendation

☐ **PASS** - System ready for production deployment  
☐ **CONDITIONAL PASS** - Deploy with known issues documented  
☐ **FAIL** - Critical issues must be resolved before deployment

### Sign-Off

**Tester Name:** _______________________  
**Date:** _______________________  
**Signature:** _______________________

**Approver Name:** _______________________  
**Date:** _______________________  
**Signature:** _______________________

---

## Appendix A: Test Data Cleanup

After testing, clean up test accounts:

```sql
DELETE FROM members WHERE call_sign LIKE 'TEST%';
DELETE FROM members WHERE call_sign = 'NEWADD1';
DELETE FROM members WHERE call_sign = 'TEST3NEW';
DELETE FROM members WHERE call_sign = 'TEST1NEW';
```

## Appendix B: Known Limitations

* Session timeout is 24 hours (cannot be changed without code modification)
* PDF export limited to ~1000 members (performance degrades beyond that)
* Email delivery depends on SMTP provider reliability
* Backup retention is 30 days (configurable in script)

## Appendix C: Browser Compatibility

Test in these browsers:
- ☐ Chrome (latest)
- ☐ Firefox (latest)
- ☐ Safari (latest)
- ☐ Edge (latest)
- ☐ Mobile Safari (iOS)
- ☐ Mobile Chrome (Android)

---

*End of Test Plan*
