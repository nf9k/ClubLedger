"""
Two-factor authentication helpers: TOTP, backup codes, and WebAuthn (YubiKey).
"""
import base64
import io
import secrets

import bcrypt
import pyotp
import qrcode
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

import os
import MySQLdb

def _get_db():
    return MySQLdb.connect(
        host=os.getenv('DB_HOST', 'db'),
        user=os.getenv('DB_USER', 'membership_user'),
        passwd=os.getenv('DB_PASSWORD', ''),
        db=os.getenv('DB_NAME', 'membership_db'),
        charset='utf8mb4',
    )

def _dict_cursor(conn):
    return conn.cursor(MySQLdb.cursors.DictCursor)

# ---------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------

def generate_totp_secret():
    return pyotp.random_base32()


def get_totp_uri(secret, call_sign):
    return pyotp.TOTP(secret).provisioning_uri(name=call_sign, issuer_name='ClubLedger')


def verify_totp(secret, code):
    """Verify a 6-digit TOTP code. valid_window=1 allows ±30s clock skew."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_qr_png(uri):
    """Return PNG bytes for a QR code encoding the given URI."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------
# Backup codes
# ---------------------------------------------------------------

BACKUP_CODE_COUNT = 8
_CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # unambiguous alphanumeric


def _make_code():
    """Return a single backup code in XXXX-XXXX format."""
    part = lambda: ''.join(secrets.choice(_CODE_CHARS) for _ in range(4))
    return f'{part()}-{part()}'


def generate_backup_codes(user_id):
    """
    Generate BACKUP_CODE_COUNT fresh backup codes for user_id.
    Replaces any existing codes. Returns plaintext list (shown once to user).
    """
    codes = [_make_code() for _ in range(BACKUP_CODE_COUNT)]
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute('DELETE FROM totp_backup_codes WHERE user_id = %s', (user_id,))
    for code in codes:
        h = bcrypt.hashpw(_normalize_code(code), bcrypt.gensalt()).decode()
        cur.execute(
            'INSERT INTO totp_backup_codes (user_id, code_hash) VALUES (%s, %s)',
            (user_id, h),
        )
    conn.commit()
    cur.close()
    conn.close()
    return codes


def verify_backup_code(user_id, code):
    """
    Check code against the user's unused backup codes.
    Marks the matching code used. Returns True on match, False otherwise.
    """
    normalized = _normalize_code(code)
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT id, code_hash FROM totp_backup_codes WHERE user_id = %s AND used = 0',
        (user_id,),
    )
    rows = cur.fetchall()
    for row in rows:
        if bcrypt.checkpw(normalized, row['code_hash'].encode()):
            cur.execute('UPDATE totp_backup_codes SET used = 1 WHERE id = %s', (row['id'],))
            conn.commit()
            cur.close()
            conn.close()
            return True
    cur.close()
    conn.close()
    return False


def unused_backup_code_count(user_id):
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT COUNT(*) AS cnt FROM totp_backup_codes WHERE user_id = %s AND used = 0',
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['cnt'] if row else 0


def _normalize_code(code):
    """Strip dashes/spaces and upper-case a backup code for comparison."""
    return code.replace('-', '').replace(' ', '').upper().encode()


# ---------------------------------------------------------------
# WebAuthn
# ---------------------------------------------------------------

def _rp_id(app):
    return app.config['WEBAUTHN_RP_ID']


def _origin(app):
    return app.config['WEBAUTHN_ORIGIN']


def webauthn_begin_registration(app, user):
    """
    Start a WebAuthn registration ceremony.
    Returns (options_json_str, challenge_b64) — store challenge_b64 in session.
    """
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT credential_id FROM webauthn_credentials WHERE user_id = %s', (user.id,)
    )
    existing = cur.fetchall()
    cur.close()
    conn.close()

    exclude = [
        PublicKeyCredentialDescriptor(id=_decode_cred_id(r['credential_id']))
        for r in existing
    ]

    options = generate_registration_options(
        rp_id=_rp_id(app),
        rp_name='ClubLedger',
        user_id=str(user.id).encode(),
        user_name=user.username,
        user_display_name=user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
            resident_key=ResidentKeyRequirement.DISCOURAGED,
        ),
    )
    challenge_b64 = base64.b64encode(options.challenge).decode()
    return options_to_json(options), challenge_b64


def webauthn_complete_registration(app, challenge_b64, response_json, user_id, key_name):
    """
    Finish a WebAuthn registration ceremony and persist the credential.
    Raises on failure.
    """
    challenge = base64.b64decode(challenge_b64)
    verified = verify_registration_response(
        credential=response_json,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(app),
        expected_origin=_origin(app),
    )
    cred_id = _encode_cred_id(verified.credential_id)
    pub_key = base64.urlsafe_b64encode(verified.credential_public_key).rstrip(b'=').decode()

    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        '''INSERT INTO webauthn_credentials (user_id, credential_id, public_key, sign_count, name)
           VALUES (%s, %s, %s, %s, %s)''',
        (user_id, cred_id, pub_key, verified.sign_count, key_name or 'Security Key'),
    )
    cur.execute('UPDATE members SET webauthn_enabled = 1 WHERE id = %s', (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def webauthn_begin_authentication(app, user_id):
    """
    Start a WebAuthn authentication ceremony.
    Returns (options_json_str, challenge_b64).
    """
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT credential_id FROM webauthn_credentials WHERE user_id = %s', (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    allow = [
        PublicKeyCredentialDescriptor(id=_decode_cred_id(r['credential_id']))
        for r in rows
    ]

    options = generate_authentication_options(
        rp_id=_rp_id(app),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    challenge_b64 = base64.b64encode(options.challenge).decode()
    return options_to_json(options), challenge_b64


def webauthn_complete_authentication(app, challenge_b64, response_json):
    """
    Finish a WebAuthn authentication ceremony.
    Returns user_id on success. Raises on failure.
    """
    import json
    challenge = base64.b64decode(challenge_b64)

    resp = json.loads(response_json) if isinstance(response_json, str) else response_json
    raw_id = resp.get('rawId') or resp.get('id', '')

    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT * FROM webauthn_credentials WHERE credential_id = %s', (raw_id,)
    )
    cred_row = cur.fetchone()
    if not cred_row:
        cur.close()
        conn.close()
        raise ValueError('Credential not found')

    pub_key_bytes = base64.urlsafe_b64decode(_pad(cred_row['public_key']))

    verified = verify_authentication_response(
        credential=response_json,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(app),
        expected_origin=_origin(app),
        credential_public_key=pub_key_bytes,
        credential_current_sign_count=cred_row['sign_count'],
    )
    cur.execute(
        'UPDATE webauthn_credentials SET sign_count = %s WHERE id = %s',
        (verified.new_sign_count, cred_row['id']),
    )
    conn.commit()
    cur.close()
    conn.close()
    return cred_row['user_id']


def get_webauthn_credentials(user_id):
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'SELECT id, name, created_at FROM webauthn_credentials WHERE user_id = %s ORDER BY created_at',
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_webauthn_credential(credential_db_id, user_id):
    """Delete a credential row, then clear webauthn_enabled if none remain."""
    conn = _get_db()
    cur = _dict_cursor(conn)
    cur.execute(
        'DELETE FROM webauthn_credentials WHERE id = %s AND user_id = %s',
        (credential_db_id, user_id),
    )
    cur.execute(
        'SELECT COUNT(*) AS cnt FROM webauthn_credentials WHERE user_id = %s', (user_id,)
    )
    if cur.fetchone()['cnt'] == 0:
        cur.execute('UPDATE members SET webauthn_enabled = 0 WHERE id = %s', (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _encode_cred_id(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b'=').decode()


def _decode_cred_id(s):
    return base64.urlsafe_b64decode(_pad(s))


def _pad(s):
    """Re-add base64 padding stripped during storage."""
    return s + '=' * (-len(s) % 4)
