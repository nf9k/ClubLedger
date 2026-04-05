#!/bin/bash

# ClubLedger Expiration Check - Cron Wrapper
# Runs the Python expiration checker inside the Docker container

cd /docker/clubledger

# Copy script and .env to container
docker cp scripts/check_expirations.py clubledger_web:/tmp/check_expirations.py
docker cp .env clubledger_web:/tmp/.env

# Run the checker
docker exec clubledger_web python3 /tmp/check_expirations.py

# Clean up
docker exec clubledger_web rm -f /tmp/check_expirations.py /tmp/.env

exit 0
