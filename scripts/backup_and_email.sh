#!/bin/bash

# ClubLedger - Database Backup Script
# Uses SMTP and recipient settings from .env

set -e

BACKUP_DIR="/docker/clubledger/backups"
DATE=$(date +%m%d%Y_%H%M)
BACKUP_NAME="clubledger_${DATE}"
RETENTION_DAYS=30

cd /docker/clubledger
source .env

# ADMIN_EMAILS is comma-separated in .env
EMAIL_TO="${ADMIN_EMAILS}"

if [ -z "$EMAIL_TO" ]; then
    echo "Warning: ADMIN_EMAILS not set in .env — backup will be saved locally only"
fi

mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Starting backup at $(date)"
echo "=========================================="

# 1. SQL Dump
docker exec clubledger_db mariadb-dump \
  -u root \
  -p"${DB_ROOT_PASSWORD}" \
  --single-transaction \
  --quick \
  --skip-lock-tables \
  --routines \
  --triggers \
  "${DB_NAME}" > "${BACKUP_DIR}/${BACKUP_NAME}.sql"

echo "✓ SQL dump completed"

# 2. Export members to CSV
docker exec clubledger_db mariadb \
  -u root \
  -p"${DB_ROOT_PASSWORD}" \
  -B "${DB_NAME}" \
  -e "SELECT call_sign, name, email, city, state, member_type, paid_thru,
      CASE WHEN is_admin = 1 THEN 'Yes' ELSE 'No' END as admin, created_at
      FROM members ORDER BY call_sign" \
  | sed 's/\t/","/g;s/^/"/;s/$/"/;s/"\([0-9]\+\)"/\1/g' > "${BACKUP_DIR}/${BACKUP_NAME}_members.csv"

echo "✓ CSV export completed"

# 3. Get stats
MEMBER_COUNT=$(docker exec clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" -sN "${DB_NAME}" -e "SELECT COUNT(*) FROM members")
ADMIN_COUNT=$(docker exec clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" -sN "${DB_NAME}" -e "SELECT COUNT(*) FROM members WHERE is_admin = 1")

echo "✓ Stats: ${MEMBER_COUNT} members (${ADMIN_COUNT} admins)"

# 4. Create ZIP archive
cd "$BACKUP_DIR"
zip -9 "${BACKUP_NAME}.zip" "${BACKUP_NAME}.sql" "${BACKUP_NAME}_members.csv"
FILESIZE=$(ls -lh "${BACKUP_NAME}.zip" | awk '{print $5}')
rm "${BACKUP_NAME}.sql" "${BACKUP_NAME}_members.csv"

echo "✓ ZIP created: ${FILESIZE}"

# 5. Send email if recipients are configured
if [ -n "$EMAIL_TO" ]; then
    cat > /tmp/send_backup_email.py << PYEOF
import smtplib
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

backup_file = '/tmp/${BACKUP_NAME}.zip'
org_name = os.getenv('ORG_NAME', 'ClubLedger')

msg = MIMEMultipart()
msg['From'] = os.getenv('SMTP_FROM_EMAIL')
msg['To'] = '${EMAIL_TO}'
msg['Subject'] = f"{org_name} Membership Backup - ${DATE} (${MEMBER_COUNT} members)"

body = f"""{org_name} Membership Database Backup
=====================================
Date: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
Backup File: ${BACKUP_NAME}.zip
Size: ${FILESIZE}
Members: ${MEMBER_COUNT}
Admins: ${ADMIN_COUNT}
Database: ${DB_NAME}

Backup Contents:
- Full SQL dump (schema + data)
- CSV export (members table)

Restore Instructions:
1. unzip ${BACKUP_NAME}.zip
2. docker exec -i clubledger_db mariadb -u root -p "${DB_NAME}" < ${BACKUP_NAME}.sql

This is an automated backup from the ClubLedger Membership Portal.
=====================================
"""

msg.attach(MIMEText(body, 'plain'))

with open(backup_file, 'rb') as f:
    part = MIMEBase('application', 'zip')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="${BACKUP_NAME}.zip"')
    msg.attach(part)

try:
    with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
        server.send_message(msg)
    print('Email sent successfully')
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
PYEOF

    docker cp "${BACKUP_DIR}/${BACKUP_NAME}.zip" clubledger_web:/tmp/${BACKUP_NAME}.zip
    docker cp /tmp/send_backup_email.py clubledger_web:/tmp/send_backup_email.py

    if docker exec clubledger_web python3 /tmp/send_backup_email.py; then
        echo "✓ Backup emailed to: ${EMAIL_TO}"
    else
        echo "✗ Failed to send email — backup saved locally at: ${BACKUP_DIR}/${BACKUP_NAME}.zip"
    fi

    docker exec clubledger_web rm -f /tmp/${BACKUP_NAME}.zip /tmp/send_backup_email.py
    rm -f /tmp/send_backup_email.py
fi

# 6. Clean up old backups
find "$BACKUP_DIR" -name "clubledger_*.zip" -type f -mtime +${RETENTION_DAYS} -delete

echo ""
echo "=========================================="
echo "Backup completed at $(date)"
echo "=========================================="
ls -lht "$BACKUP_DIR"/clubledger_*.zip 2>/dev/null | head -5
