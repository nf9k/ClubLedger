#!/bin/bash

# ClubLedger - Expiration Notification System Setup

set -e

echo "=========================================="
echo "ClubLedger Expiration Notification Setup"
echo "=========================================="
echo ""

cd /docker/clubledger

if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

source .env

# 1. Add database columns
echo "Step 1: Adding database tracking columns..."
docker exec -i clubledger_db mariadb -u root -p"${DB_ROOT_PASSWORD}" "${DB_NAME}" < database/add_expiration_tracking.sql

echo "✓ Database updated"
echo ""

# 2. Make scripts executable
echo "Step 2: Setting up notification script..."
chmod +x scripts/check_expirations.py scripts/run_expiration_check.sh

echo "✓ Scripts ready"
echo ""

# 3. Test the script
echo "Step 3: Testing notification check..."
echo "This will check for status changes and may send notifications if statuses have changed."
read -p "Press Enter to continue..."

docker cp scripts/check_expirations.py clubledger_web:/tmp/check_expirations.py
docker cp .env clubledger_web:/tmp/.env

docker exec clubledger_web python3 /tmp/check_expirations.py

docker exec clubledger_web rm /tmp/check_expirations.py /tmp/.env

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Review the test output above"
echo "2. Add to crontab for daily checks:"
echo ""
echo "   crontab -e"
echo ""
echo "   Add this line:"
echo "   0 9 * * * /docker/clubledger/scripts/run_expiration_check.sh >> /docker/clubledger/backups/expiration_check.log 2>&1"
echo ""
echo "To manually run a check:"
echo "   ./scripts/run_expiration_check.sh"
echo ""
echo "=========================================="
