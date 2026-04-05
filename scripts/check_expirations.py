#!/usr/bin/env python3
"""
IRC Membership Expiration Notification Script

Checks member expiration status and sends notifications when status changes.
Runs via cron - only sends emails when status actually changes.

Status Definitions:
- ACTIVE: Paid through a future year (2027+)
- EXPIRING: Paid through current year (2026)
- EXPIRED: Paid through a past year (2025 or earlier)

Notifications are sent when status changes, not on a schedule.
This prevents spam while keeping members informed.
"""

import smtplib
import os
import sys
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import MySQLdb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_CONFIG = {
    'host': 'db',
    'user': os.getenv('DB_USER'),
    'passwd': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}

SMTP_CONFIG = {
    'host': os.getenv('SMTP_HOST'),
    'port': int(os.getenv('SMTP_PORT', 587)),
    'user': os.getenv('SMTP_USER'),
    'password': os.getenv('SMTP_PASSWORD'),
    'from_email': os.getenv('SMTP_FROM_EMAIL')
}

APP_URL          = os.getenv('APP_URL', 'http://localhost:5000')
ORG_NAME         = os.getenv('ORG_NAME', 'Ham Radio Club')
SERVICE_DESK_URL = os.getenv('SERVICE_DESK_URL', '')
ADMIN_EMAILS     = [e.strip() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()]

def get_current_status(paid_thru):
    """Determine current status based on paid_thru year"""
    if not paid_thru:
        return 'unknown'
    
    try:
        paid_year = int(paid_thru)
        current_year = date.today().year
        
        if paid_year < current_year:
            # Paid through past year = expired
            return 'expired'
        elif paid_year == current_year:
            # Paid through current year = expiring
            return 'expiring'
        else:  # paid_year > current_year
            # Paid through future year = active
            return 'active'
    except (ValueError, TypeError):
        return 'unknown'

def send_member_notification(member, new_status):
    """Send expiration notification to member"""
    
    if not member['email']:
        return False, "No email address"
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['from_email']
    msg['To'] = member['email']
    
    # Customize subject and body based on status
    contact_line = f"Website: https://{SERVICE_DESK_URL}" if SERVICE_DESK_URL else ""

    if new_status == 'expired':
        msg['Subject'] = f"{ORG_NAME} Membership Expired - {member['call_sign']}"
        body = f"""Hello {member['call_sign']},

This is a notification that your {ORG_NAME} membership has EXPIRED.

Your membership was paid through: {member['paid_thru'] or 'Unknown'}
Current year: {date.today().year}

To renew your membership and maintain your benefits, please contact us regarding renewal and payment options.

You can still access the membership portal to update your contact information at:
{APP_URL}

If you have already renewed, please disregard this message. It may take a few days for the system to reflect your payment.
{contact_line}

Thank you for your past support of {ORG_NAME}!

73,
{ORG_NAME}
Membership Team
"""

    elif new_status == 'expiring':
        msg['Subject'] = f"{ORG_NAME} Membership Expiring Soon - {member['call_sign']}"
        body = f"""Hello {member['call_sign']},

This is a friendly reminder that your {ORG_NAME} membership expires at the end of this year.

Your membership is paid through: {member['paid_thru']}
Current year: {date.today().year}

To ensure uninterrupted membership, please renew before December 31, {date.today().year}.
{contact_line}

You can access the membership portal at any time to update your information:
{APP_URL}

Thank you for your continued support of {ORG_NAME}!

73,
{ORG_NAME}
Membership Team
"""

    elif new_status == 'active':
        msg['Subject'] = f"{ORG_NAME} Membership Active - {member['call_sign']}"
        body = f"""Hello {member['call_sign']},

Thank you! Your {ORG_NAME} membership is now ACTIVE.

Your membership is paid through: {member['paid_thru']}

You can access the membership portal at:
{APP_URL}
{contact_line}

Thank you for supporting {ORG_NAME}!

73,
{ORG_NAME}
Membership Team
"""
    else:
        return False, "Unknown status"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.send_message(msg)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

def send_admin_summary(notifications):
    """Send summary of notifications to administrators"""
    
    if not notifications:
        return
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['from_email']
    msg['To'] = ', '.join(ADMIN_EMAILS)
    msg['Subject'] = f"{ORG_NAME} Membership Expiration Notifications - {date.today().strftime('%Y-%m-%d')}"
    
    # Build summary
    expired_count = sum(1 for n in notifications if n['new_status'] == 'expired')
    expiring_count = sum(1 for n in notifications if n['new_status'] == 'expiring')
    renewed_count = sum(1 for n in notifications if n['new_status'] == 'active')
    failed_count = sum(1 for n in notifications if not n['sent'])
    
    body = f"""IRC Membership Expiration Notification Summary
=========================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Notifications Sent: {len([n for n in notifications if n['sent']])}
Failed to Send: {failed_count}

Status Changes:
- Now Expired: {expired_count}
- Expiring Soon: {expiring_count}
- Renewed/Active: {renewed_count}

Details:
"""
    
    for notif in notifications:
        status_icon = "✓" if notif['sent'] else "✗"
        body += f"\n{status_icon} {notif['call_sign']} ({notif['old_status']} → {notif['new_status']})"
        if notif['email']:
            body += f" - {notif['email']}"
        else:
            body += " - NO EMAIL"
        if not notif['sent']:
            body += f" - FAILED: {notif['error']}"
    
    body += f"""

Total Active Members: {notifications[0]['total_active'] if notifications else 0}
Total Expiring Soon: {notifications[0]['total_expiring'] if notifications else 0}
Total Expired: {notifications[0]['total_expired'] if notifications else 0}

Members Without Email Addresses:
"""
    
    # Add members without email
    if notifications and notifications[0].get('no_email_members'):
        for member in notifications[0]['no_email_members']:
            body += f"\n  • {member['call_sign']} ({member['status']})"
    else:
        body += "\n  (none)"
    
    body += """

Action Required:
- Review failed notifications
- Contact members without email addresses
- Update membership records as needed

Access the membership portal:
""" + APP_URL + f"""

73,
{ORG_NAME} Membership Notification System
"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.send_message(msg)
        print("✓ Admin summary sent")
    except Exception as e:
        print(f"✗ Failed to send admin summary: {e}")

def main():
    print("=" * 60)
    print("IRC Membership Expiration Notification Check")
    print("=" * 60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = MySQLdb.connect(**DB_CONFIG)
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Get all members
    cursor.execute("""
        SELECT id, call_sign, name, email, paid_thru, 
               expiration_status, expiration_notice_sent
        FROM members
        ORDER BY call_sign
    """)
    members = cursor.fetchall()
    
    print(f"Checking {len(members)} members...\n")
    
    notifications = []
    status_changes = 0
    
    # Get overall statistics
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN CAST(paid_thru AS UNSIGNED) > YEAR(CURDATE()) THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN CAST(paid_thru AS UNSIGNED) = YEAR(CURDATE()) THEN 1 ELSE 0 END) as expiring,
            SUM(CASE WHEN CAST(paid_thru AS UNSIGNED) < YEAR(CURDATE()) THEN 1 ELSE 0 END) as expired
        FROM members
        WHERE paid_thru IS NOT NULL AND paid_thru != ''
    """)
    stats = cursor.fetchone()
    
    # Get members without email
    cursor.execute("""
        SELECT call_sign, paid_thru
        FROM members
        WHERE (email IS NULL OR email = '')
        AND paid_thru IS NOT NULL
        ORDER BY call_sign
    """)
    no_email_members = [
        {'call_sign': m['call_sign'], 'status': get_current_status(m['paid_thru'])}
        for m in cursor.fetchall()
    ]
    
    for member in members:
        current_status = get_current_status(member['paid_thru'])
        old_status = member['expiration_status'] or 'unknown'
        
        # Check if status changed
        if current_status != old_status:
            status_changes += 1
            print(f"Status change: {member['call_sign']} ({old_status} → {current_status})")
            
            # Send notification to member
            sent, error = send_member_notification(member, current_status)
            
            if sent:
                print(f"  ✓ Notification sent to {member['email']}")
                
                # Update database
                cursor.execute("""
                    UPDATE members
                    SET expiration_status = %s,
                        expiration_notice_sent = CURDATE()
                    WHERE id = %s
                """, (current_status, member['id']))
                conn.commit()
            else:
                print(f"  ✗ Failed to send: {error}")
            
            # Track for admin summary
            notifications.append({
                'call_sign': member['call_sign'],
                'email': member['email'],
                'old_status': old_status,
                'new_status': current_status,
                'sent': sent,
                'error': error if not sent else None,
                'total_active': stats['active'] or 0,
                'total_expiring': stats['expiring'] or 0,
                'total_expired': stats['expired'] or 0,
                'no_email_members': no_email_members
            })
    
    print(f"\n{'-' * 60}")
    print(f"Status changes detected: {status_changes}")
    print(f"Notifications sent: {len([n for n in notifications if n['sent']])}")
    print(f"Failed: {len([n for n in notifications if not n['sent']])}")
    print(f"{'-' * 60}\n")
    
    # Send admin summary if there were any notifications
    if notifications:
        print("Sending admin summary...")
        send_admin_summary(notifications)
    else:
        print("No status changes - no notifications sent")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Check complete")
    print("=" * 60)

if __name__ == '__main__':
    main()
