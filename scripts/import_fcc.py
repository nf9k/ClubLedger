#!/usr/bin/env python3
"""
Download and import FCC ULS Amateur Radio license data into fcc_licenses table.

Downloads the complete weekly ULS amateur zip from data.fcc.gov, parses the
EN (entity), AM (amateur class), and HD (header/status) files, and upserts
all records into the fcc_licenses table.

Usage:
    python scripts/import_fcc.py [--daily]

    --daily  Use the daily incremental zip instead of the weekly complete zip.

Environment variables (from .env):
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
"""

import argparse
import csv
import io
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import MySQLdb
import MySQLdb.cursors
import requests
from dotenv import load_dotenv

COMPLETE_URL = 'https://data.fcc.gov/download/pub/uls/complete/l_amat.zip'
DAILY_URL    = 'https://data.fcc.gov/download/pub/uls/daily/l_am_a.zip'

CLASS_MAP = {
    'E': 'Extra',
    'A': 'Advanced',
    'G': 'General',
    'T': 'Technician',
    'N': 'Novice',
    'P': 'Technician Plus',
}


def get_conn():
    load_dotenv(Path(__file__).parent.parent / '.env')
    return MySQLdb.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        passwd=os.environ['DB_PASSWORD'],
        db=os.environ['DB_NAME'],
        charset='utf8mb4',
    )


def _read_dat(zf, name):
    target  = name.lower()
    matched = next((n for n in zf.namelist() if n.lower() == target), None)
    if matched is None:
        print(f'  Warning: {name} not found in zip (skipping)', flush=True)
        return []
    with zf.open(matched) as fh:
        text = fh.read().decode('latin-1')
    return list(csv.reader(io.StringIO(text), delimiter='|'))


def parse_hd(zf):
    hd = {}
    for row in _read_dat(zf, 'HD.dat'):
        if len(row) < 6:
            continue
        usi = row[1].strip()
        if usi:
            hd[usi] = row[5].strip()
    return hd


def parse_en(zf):
    en = {}
    for row in _read_dat(zf, 'EN.dat'):
        if len(row) < 19:
            continue
        usi  = row[1].strip()
        call = row[4].strip().upper()
        if not usi or not call:
            continue
        en[usi] = {
            'callsign': call,
            'fname':   row[8].strip()  or None,
            'mi':      row[9].strip()  or None,
            'lname':   row[10].strip() or None,
            'suffix':  row[11].strip() or None,
            'address': row[15].strip() or None,
            'city':    row[16].strip() or None,
            'state':   row[17].strip() or None,
            'zip':     row[18].strip() or None,
        }
    return en


def parse_am(zf):
    am = {}
    for row in _read_dat(zf, 'AM.dat'):
        if len(row) < 6:
            continue
        usi = row[1].strip()
        cls = row[5].strip()
        if usi and cls:
            am[usi] = CLASS_MAP.get(cls, cls)
    return am


def run(daily=False):
    url   = DAILY_URL if daily else COMPLETE_URL
    label = 'daily' if daily else 'complete'

    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] Downloading FCC ULS {label} file…', flush=True)
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        tmp_path = tmp.name
        total = 0
        for chunk in resp.iter_content(65536):
            tmp.write(chunk)
            total += len(chunk)
    print(f'  Downloaded {total / 1_048_576:.1f} MB', flush=True)

    print('  Parsing…', flush=True)
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            hd = parse_hd(zf)
            en = parse_en(zf)
            am = parse_am(zf)
    finally:
        os.unlink(tmp_path)

    print(f'  HD: {len(hd):,}  EN: {len(en):,}  AM: {len(am):,}', flush=True)

    # Build raw rows keyed by USI, then deduplicate by callsign.
    # EN.dat can contain multiple USI rows for the same callsign (prior holders +
    # current holder after reassignment). Prefer status='A' (Active); among ties
    # take the last USI seen — same last-row-wins behaviour as before but only
    # among records that share the winning status tier.
    raw = {}
    for usi, entity in en.items():
        raw[usi] = (
            entity['callsign'], entity['fname'], entity['mi'],
            entity['lname'],    entity['suffix'], entity['address'],
            entity['city'],     entity['state'],  entity['zip'],
            am.get(usi),        hd.get(usi) or None,
        )

    best = {}   # callsign -> best row
    for row in raw.values():
        call   = row[0]
        status = row[10]   # license_status: 'A'=Active, 'E'=Expired, 'C'=Cancelled, etc.
        prev   = best.get(call)
        if prev is None or (status == 'A' and prev[10] != 'A'):
            best[call] = row
    rows = list(best.values())

    print(f'  Upserting {len(rows):,} rows…', flush=True)
    conn = get_conn()
    cur  = conn.cursor()

    if not daily:
        cur.execute('TRUNCATE TABLE fcc_licenses')
        conn.commit()

    BATCH = 2000
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        if daily:
            cur.executemany('''
                INSERT INTO fcc_licenses
                    (callsign, fname, mi, lname, suffix, address, city, state, zip,
                     license_class, license_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    fname=VALUES(fname), mi=VALUES(mi), lname=VALUES(lname),
                    suffix=VALUES(suffix), address=VALUES(address), city=VALUES(city),
                    state=VALUES(state), zip=VALUES(zip),
                    license_class=VALUES(license_class), license_status=VALUES(license_status),
                    updated_at=CURRENT_TIMESTAMP
            ''', batch)
        else:
            cur.executemany('''
                INSERT IGNORE INTO fcc_licenses
                    (callsign, fname, mi, lname, suffix, address, city, state, zip,
                     license_class, license_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', batch)
        conn.commit()
        if (i // BATCH) % 50 == 0:
            print(f'    …{i + len(batch):,} done', flush=True)

    cur.close()
    conn.close()
    print(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] Import complete.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import FCC ULS amateur license data')
    parser.add_argument('--daily', action='store_true',
                        help='Use daily incremental zip (upsert) instead of full replace')
    args = parser.parse_args()
    try:
        run(daily=args.daily)
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
