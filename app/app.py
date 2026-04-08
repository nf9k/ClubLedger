import hmac
import io
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import MySQLdb
import requests
from flask_mail import Mail, Message

app = Flask(__name__)

_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    raise RuntimeError('SECRET_KEY environment variable must be set')
app.config['SECRET_KEY'] = _secret_key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('APP_URL', '').startswith('https')

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[], storage_uri='memory://')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'user': os.getenv('DB_USER', 'membership_user'),
    'passwd': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'membership_db'),
    'charset': 'utf8mb4'
}

# Mail configuration
app.config['MAIL_SERVER'] = os.getenv('SMTP_HOST', 'mail.smtp2go.com')
app.config['MAIL_PORT'] = int(os.getenv('SMTP_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('SMTP_USER', '')
app.config['MAIL_PASSWORD'] = os.getenv('SMTP_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('SMTP_FROM_EMAIL', 'noreply@example.com')

# WebAuthn config (derived from APP_URL)
_app_url = os.getenv('APP_URL', 'http://localhost:5000')
_parsed_url = urllib.parse.urlparse(_app_url)
app.config['WEBAUTHN_RP_ID'] = _parsed_url.hostname
app.config['WEBAUTHN_ORIGIN'] = f"{_parsed_url.scheme}://{_parsed_url.netloc}"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Organisation branding
ORG_NAME         = os.getenv('ORG_NAME', 'Ham Radio Club')
SERVICE_DESK_URL = os.getenv('SERVICE_DESK_URL', '')
LOGO_FILENAME    = os.getenv('LOGO_FILENAME', '')

# hCaptcha (both keys must be set to activate; app works normally without them)
HCAPTCHA_SITE_KEY   = os.getenv('HCAPTCHA_SITE_KEY', '')
HCAPTCHA_SECRET_KEY = os.getenv('HCAPTCHA_SECRET_KEY', '')

VERSION = 'v1.12'
APP_CREDIT = f'ClubLedger {VERSION} by NF9K'

# Demo mode
DEMO_MODE        = os.getenv('DEMO_MODE', 'false').lower() == 'true'
DEMO_RESET_TOKEN = os.getenv('DEMO_RESET_TOKEN', '')

if DEMO_MODE:
    mail = Mail(app)
    mail.send = lambda msg: app.logger.debug('Demo mode: suppressed email to %s', msg.recipients)
else:
    mail = Mail(app)

@app.context_processor
def inject_org():
    return dict(org_name=ORG_NAME, service_desk_url=SERVICE_DESK_URL, logo_filename=LOGO_FILENAME,
                app_credit=APP_CREDIT, hcaptcha_site_key=HCAPTCHA_SITE_KEY,
                demo_mode=DEMO_MODE)

# Database helper functions
def get_db_connection():
    """Create database connection"""
    return MySQLdb.connect(**DB_CONFIG)

def dict_cursor(conn):
    """Create a cursor that returns results as dictionaries"""
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    return cursor

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, is_admin):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT id, call_sign, email, is_admin FROM members WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_data:
        return User(user_data['id'], user_data['call_sign'], user_data['email'], user_data['is_admin'])
    return None

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Check if password matches hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_reset_token():
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def _safe_redirect_url(target):
    """Return target only if it is a safe relative URL, otherwise dashboard."""
    if not target:
        return url_for('dashboard')
    parsed = urllib.parse.urlparse(target)
    if parsed.scheme or parsed.netloc:
        return url_for('dashboard')
    return target

def _verify_hcaptcha():
    """Verify hCaptcha response. Returns True if keys not configured (safe default)."""
    if not HCAPTCHA_SITE_KEY or not HCAPTCHA_SECRET_KEY:
        return True
    token = request.form.get('h-captcha-response', '')
    try:
        resp = requests.post(
            'https://hcaptcha.com/siteverify',
            data={'secret': HCAPTCHA_SECRET_KEY, 'response': token},
            timeout=5,
        )
        return resp.json().get('success', False)
    except Exception:
        return False

DIFF_FIELD_LABELS = {
    'call_sign':    'Call Sign',
    'email':        'Email',
    'name':         'Name',
    'primary_rep':  'Primary Repeater',
    'rep_call':     'Repeater Call Sign',
    'address':      'Address',
    'city':         'City',
    'state':        'State',
    'zip':          'ZIP',
    'telephone':    'Phone',
    'paid_thru':    'Paid Through',
    'member_type':  'Member Type',
    'is_admin':     'Administrator',
}

def send_record_change_email(member_email, call_sign, changes):
    """Email the member a summary of what changed on their record."""
    def fmt(val, label):
        if label == 'Administrator':
            return 'Yes' if val else 'No'
        return str(val) if val not in (None, '') else '(blank)'

    lines = []
    for label, old_val, new_val in changes:
        lines.append(f"  {label}: {fmt(old_val, label)}  →  {fmt(new_val, label)}")

    contact_line = f"If you did not make these changes or have questions, please contact us at {SERVICE_DESK_URL}" if SERVICE_DESK_URL else "If you did not make these changes or have questions, please contact an administrator."

    msg = Message(
        subject=f"Your {ORG_NAME} membership record has been updated",
        recipients=[member_email],
        body=f"""Hello {call_sign},

Your membership record with {ORG_NAME} has been updated.

The following fields were changed:

{chr(10).join(lines)}

{contact_line}

73,
{APP_CREDIT}
"""
    )
    try:
        mail.send(msg)
    except Exception as e:
        app.logger.error('Error sending record change email: %s', e)


def send_password_reset_email(user_email, call_sign, token):
    """Send password reset email"""
    reset_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/reset-password/{token}"
    
    msg = Message(
        subject="Password Reset Request",
        recipients=[user_email],
        body=f"""Hello {call_sign},

You have requested to reset your password for the {ORG_NAME} Membership Portal.

Please click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email.

73,
{APP_CREDIT}
"""
    )
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error('Error sending email: %s', e)
        return False

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10/minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if not _verify_hcaptcha():
            flash('Please complete the CAPTCHA.', 'danger')
            return render_template('login.html')
        call_sign = request.form.get('call_sign').upper()
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute(
            "SELECT id, call_sign, email, password_hash, is_admin, totp_enabled, webauthn_enabled "
            "FROM members WHERE call_sign = %s", (call_sign,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_data and check_password(password, user_data['password_hash']):
            if user_data['totp_enabled'] or user_data['webauthn_enabled']:
                session['pending_2fa_user_id'] = user_data['id']
                session['pending_2fa_next'] = _safe_redirect_url(request.form.get('next'))
                return redirect(url_for('twofa_challenge'))
            user = User(user_data['id'], user_data['call_sign'], user_data['email'], user_data['is_admin'])
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid call sign or password', 'danger')
    
    return render_template('login.html')

@app.route('/request-access', methods=['POST'])
def request_access():
    """Handle password recovery/access request"""
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash('Please enter an email address.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT id, call_sign, email FROM members WHERE email = %s", (email,))
    user = cursor.fetchone()
    
    if user:
        # Generate reset token
        token = generate_reset_token()
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at) 
            VALUES (%s, %s, %s)
        """, (user['id'], token, expires_at))
        conn.commit()
        
        # Send email with login instructions
        send_password_reset_email(user['email'], user['call_sign'], token)
        flash('Login instructions have been sent to your email address.', 'success')
    else:
        # Email not found - redirect to service desk
        contact_hint = f" Please visit {SERVICE_DESK_URL} to request access." if SERVICE_DESK_URL else " Please contact an administrator to request access."
        flash(f'Email address not found in our system.{contact_hint}', 'info')
    
    cursor.close()
    conn.close()
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    if current_user.is_admin:
        cursor.execute("SELECT * FROM members ORDER BY name")
        members = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM members WHERE id = %s", (current_user.id,))
        members = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', members=members, now=datetime.now())


@app.route('/admin/export-pdf')
@login_required
@admin_required
def export_pdf():
    """Generate and download PDF of member database"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    # Title
    title = Paragraph(f"{ORG_NAME}<br/>Membership Database", title_style)
    elements.append(title)
    
    # Subtitle with date and count
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    cursor.execute("SELECT COUNT(*) as count FROM members")
    member_count = cursor.fetchone()['count']
    
    subtitle = Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
                        f"Total Members: {member_count}", subtitle_style)
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))
    
    # Get member data
    cursor.execute("""
        SELECT call_sign, name, email, city, state, member_type, paid_thru,
               CASE WHEN is_admin = 1 THEN 'Yes' ELSE 'No' END as admin
        FROM members 
        ORDER BY 
            CASE 
                WHEN name LIKE '% %' THEN SUBSTRING_INDEX(name, ' ', -1)
                ELSE name
            END,
            name
    """)
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Create paragraph style for table cells
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    
    cell_style = ParagraphStyle(
        'CellStyle',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        wordWrap='CJK'
    )
    
    # Prepare table data with Paragraphs for wrapping
    table_data = [[
        'Call Sign', 'Name', 'Email', 'City', 'State', 
        'Type', 'Paid Thru', 'Admin'
    ]]
    
    for member in members:
        table_data.append([
            Paragraph(member['call_sign'] or '', cell_style),
            Paragraph(member['name'] or '', cell_style),
            Paragraph(member['email'] or '', cell_style),
            Paragraph(member['city'] or '', cell_style),
            Paragraph(member['state'] or '', cell_style),
            Paragraph(member['member_type'] or '', cell_style),
            Paragraph(member['paid_thru'] or '', cell_style),
            Paragraph(member['admin'] or '', cell_style)
        ])
    
    # Create table with adjusted column widths for landscape letter (10.5" available width)
    # Total: 0.8 + 1.5 + 2.0 + 1.0 + 0.4 + 0.7 + 0.7 + 0.5 = 7.6 inches
    table = Table(table_data, colWidths=[
        0.8*inch,   # Call Sign
        1.5*inch,   # Name
        2.0*inch,   # Email
        1.0*inch,   # City
        0.4*inch,   # State
        0.7*inch,   # Type
        0.7*inch,   # Paid Thru
        0.5*inch    # Admin
    ])
    
    # Table style
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Call sign left
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Changed to TOP for better text alignment
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        
        # Padding
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    footer = Paragraph(f"{ORG_NAME} Membership Portal<br/>"
                      f"This document contains confidential member information. &nbsp;|&nbsp; {APP_CREDIT}",
                      footer_style)
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Prepare response
    buffer.seek(0)
    safe_org = ORG_NAME.replace(' ', '_')
    filename = f"{safe_org}_Membership_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    from flask import send_file
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def profile(user_id):
    # Check permissions
    if not current_user.is_admin and current_user.id != user_id:
        flash('You do not have permission to edit this profile.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    if request.method == 'POST':
        # Capture full before-state for change tracking
        cursor.execute("SELECT * FROM members WHERE id = %s", (user_id,))
        old_member = cursor.fetchone()

        # Get call sign - only admins can change it
        if current_user.is_admin:
            new_call_sign = request.form.get('call_sign').upper()
        else:
            new_call_sign = old_member['call_sign']

        # Get other form data
        email = request.form.get('email')
        name = request.form.get('name')
        primary_rep = request.form.get('primary_rep')
        rep_call = request.form.get('rep_call').upper() if request.form.get('rep_call') else None
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        telephone = request.form.get('telephone')

        # Admin-only field
        admin_comments = None
        if current_user.is_admin:
            admin_comments = request.form.get('admin_comments', '')
            # Limit to 500 characters
            if admin_comments and len(admin_comments) > 500:
                admin_comments = admin_comments[:500]

        old_call_sign = old_member['call_sign']
        call_sign_changed = (new_call_sign != old_call_sign)
        
        # If call sign changed, check for duplicates
        if call_sign_changed:
            cursor.execute("SELECT id FROM members WHERE call_sign = %s AND id != %s", 
                         (new_call_sign, user_id))
            if cursor.fetchone():
                flash(f'Call sign {new_call_sign} is already in use.', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('profile', user_id=user_id))
        
        # Build update query - paid_thru, member_type, and call_sign only editable by admin
        if current_user.is_admin:
            paid_thru = request.form.get('paid_thru')
            member_type = request.form.get('member_type')
            
            # Only update is_admin if editing someone else
            # If editing yourself, preserve current admin status
            if user_id == current_user.id:
                # Editing own profile - don't change admin status
                cursor.execute("""
                    UPDATE members 
                    SET call_sign = %s, email = %s, name = %s, primary_rep = %s, rep_call = %s,
                        address = %s, city = %s, state = %s, zip = %s, telephone = %s,
                        paid_thru = %s, member_type = %s, admin_comments = %s
                    WHERE id = %s
                """, (new_call_sign, email, name, primary_rep, rep_call, address, city, state, zip_code, 
                      telephone, paid_thru, member_type, admin_comments, user_id))
            else:
                # Editing someone else - allow changing admin status
                is_admin = 1 if request.form.get('is_admin') == 'on' else 0
                cursor.execute("""
                    UPDATE members 
                    SET call_sign = %s, email = %s, name = %s, primary_rep = %s, rep_call = %s,
                        address = %s, city = %s, state = %s, zip = %s, telephone = %s,
                        paid_thru = %s, member_type = %s, is_admin = %s, admin_comments = %s
                    WHERE id = %s
                """, (new_call_sign, email, name, primary_rep, rep_call, address, city, state, zip_code, 
                      telephone, paid_thru, member_type, is_admin, admin_comments, user_id))
        else:
            # Non-admin update (call_sign already fetched from DB above)
            cursor.execute("""
                UPDATE members 
                SET email = %s, name = %s, primary_rep = %s, rep_call = %s,
                    address = %s, city = %s, state = %s, zip = %s, telephone = %s
                WHERE id = %s
            """, (email, name, primary_rep, rep_call, address, city, state, zip_code, 
                  telephone, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()

        # Build diff of changed fields and email the member if anything changed
        new_values = {
            'call_sign':   new_call_sign,
            'email':       email,
            'name':        name,
            'primary_rep': primary_rep,
            'rep_call':    rep_call,
            'address':     address,
            'city':        city,
            'state':       state,
            'zip':         zip_code,
            'telephone':   telephone,
        }
        if current_user.is_admin:
            if current_user.id != user_id:
                is_admin_new = 1 if request.form.get('is_admin') == 'on' else 0
            else:
                is_admin_new = old_member['is_admin']
            new_values['paid_thru']    = request.form.get('paid_thru')
            new_values['member_type']  = request.form.get('member_type')
            new_values['is_admin']     = is_admin_new

        changes = []
        for field, label in DIFF_FIELD_LABELS.items():
            if field not in new_values:
                continue
            old_val = old_member.get(field)
            new_val = new_values[field]
            # Normalise to strings for comparison; treat None and '' as equivalent
            old_str = str(old_val) if old_val not in (None, '') else ''
            new_str = str(new_val) if new_val not in (None, '') else ''
            if old_str != new_str:
                changes.append((label, old_val, new_val))

        # Determine recipient email (use new email if it changed, otherwise old)
        recipient_email = new_values.get('email') or old_member.get('email')
        if changes and recipient_email:
            send_record_change_email(recipient_email, new_call_sign, changes)

        # If admin changed someone else's call sign, notify them
        if call_sign_changed and user_id != current_user.id:
            flash(f'Call sign updated to {new_call_sign}. Member will need to login with new call sign.', 'success')
            return redirect(url_for('dashboard'))

        # If admin changed their own call sign, log them out
        if call_sign_changed and user_id == current_user.id:
            logout_user()
            flash(f'Call sign updated to {new_call_sign}. Please login with your new call sign.', 'success')
            return redirect(url_for('login'))

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    # GET request - display profile
    cursor.execute("SELECT * FROM members WHERE id = %s", (user_id,))
    member = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('profile.html', member=member)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return render_template('change_password.html')
        
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT password_hash FROM members WHERE id = %s", (current_user.id,))
        user_data = cursor.fetchone()
        
        if not check_password(current_password, user_data['password_hash']):
            flash('Current password is incorrect.', 'danger')
            cursor.close()
            conn.close()
            return render_template('change_password.html')
        
        new_hash = hash_password(new_password)
        cursor.execute("UPDATE members SET password_hash = %s WHERE id = %s", (new_hash, current_user.id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

@app.route('/admin/initiate-reset/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def initiate_password_reset(user_id):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    cursor.execute("SELECT call_sign, email FROM members WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Generate reset token
    token = generate_reset_token()
    expires_at = datetime.now() + timedelta(hours=24)
    
    cursor.execute("""
        INSERT INTO password_reset_tokens (user_id, token, expires_at) 
        VALUES (%s, %s, %s)
    """, (user_id, token, expires_at))
    conn.commit()
    
    # Send email
    if send_password_reset_email(user['email'], user['call_sign'], token):
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': f'Password reset email sent to {user["email"]}'})
    else:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'Failed to send email. Check SMTP configuration.'}), 500


@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5/minute', methods=['POST'])
def forgot_password():
    if request.method == 'POST':
        if not _verify_hcaptcha():
            flash('Please complete the CAPTCHA.', 'danger')
            return render_template('forgot_password.html')
        email = request.form.get('email')
        
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT id, call_sign, email FROM members WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            # Generate reset token
            token = generate_reset_token()
            expires_at = datetime.now() + timedelta(hours=24)
            
            cursor.execute("""
                INSERT INTO password_reset_tokens (user_id, token, expires_at) 
                VALUES (%s, %s, %s)
            """, (user['id'], token, expires_at))
            conn.commit()
            
            send_password_reset_email(user['email'], user['call_sign'], token)
        
        # Always show success message to prevent email enumeration
        flash('If that email exists in our system, a password reset link has been sent.', 'info')
        cursor.close()
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    cursor = dict_cursor(conn)
    
    # Verify token
    cursor.execute("""
        SELECT user_id FROM password_reset_tokens 
        WHERE token = %s AND expires_at > NOW() AND used = FALSE
    """, (token,))
    token_data = cursor.fetchone()
    
    if not token_data:
        flash('Invalid or expired password reset link.', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            cursor.close()
            conn.close()
            return render_template('reset_password.html', token=token)
        
        # Update password
        new_hash = hash_password(new_password)
        cursor.execute("UPDATE members SET password_hash = %s WHERE id = %s", 
                      (new_hash, token_data['user_id']))
        
        # Mark token as used
        cursor.execute("UPDATE password_reset_tokens SET used = TRUE WHERE token = %s", (token,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Password reset successfully! You can now log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    cursor.close()
    conn.close()
    return render_template('reset_password.html', token=token)

@app.route('/admin/add-member', methods=['GET', 'POST'])
@login_required
@admin_required
def add_member():
    if request.method == 'POST':
        call_sign = request.form.get('call_sign').upper()
        email = request.form.get('email')
        # Auto-generate secure random password
        password = secrets.token_urlsafe(16)  # Generates random 16-char password
        name = request.form.get('name')
        primary_rep = request.form.get('primary_rep')
        rep_call = request.form.get('rep_call').upper() if request.form.get('rep_call') else None
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        telephone = request.form.get('telephone')
        paid_thru = request.form.get('paid_thru')
        member_type = request.form.get('member_type')
        is_admin = 1 if request.form.get('is_admin') == 'on' else 0
        admin_comments = request.form.get('admin_comments', '')
        if admin_comments and len(admin_comments) > 500:
            admin_comments = admin_comments[:500]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO members (call_sign, password_hash, email, name, primary_rep, 
                                   rep_call, address, city, state, zip, telephone, 
                                   paid_thru, member_type, is_admin, admin_comments)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (call_sign, password_hash, email, name, primary_rep, rep_call, address, 
                  city, state, zip_code, telephone, paid_thru, member_type, is_admin, admin_comments))
            conn.commit()
            
            # Send welcome email with password reset link if email provided
            if email:
                try:
                    send_password_reset_email(email, call_sign)
                    flash(f'Member {call_sign} added successfully! Password reset email sent to {email}.', 'success')
                except Exception as e:
                    flash(f'Member {call_sign} added, but failed to send password reset email: {str(e)}', 'warning')
            else:
                flash(f'Member {call_sign} added successfully! Note: No email provided - member will need admin assistance to set password.', 'warning')
            
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        except MySQLdb.IntegrityError as e:
            flash('Call sign or email already exists.', 'danger')
            cursor.close()
            conn.close()
    
    return render_template('add_member.html')

@app.route('/zip-lookup/<zip_code>')
@login_required
def zip_lookup(zip_code):
    conn = get_db_connection()
    cur  = dict_cursor(conn)
    cur.execute(
        'SELECT DISTINCT city, state FROM fcc_licenses WHERE zip = %s LIMIT 5',
        (zip_code.strip(),)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {'city': r['city'].title() if r['city'] else '', 'state': r['state'].upper() if r['state'] else ''}
        for r in rows
    ])


@app.route('/admin/fcc-lookup/<callsign>')
@login_required
@admin_required
def fcc_lookup(callsign):
    conn = get_db_connection()
    cur  = dict_cursor(conn)
    cur.execute('SELECT * FROM fcc_licenses WHERE callsign = %s', (callsign.strip().upper(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({'found': False})
    if row.get('updated_at'):
        row['updated_at'] = str(row['updated_at'])
    return jsonify({'found': True, **row})


@app.route('/admin/delete-member/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_member(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM members WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Member deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

# ---------------------------------------------------------------
# Two-Factor Authentication routes
# ---------------------------------------------------------------

@app.route('/2fa/challenge', methods=['GET', 'POST'])
@limiter.limit('10/minute', methods=['POST'])
def twofa_challenge():
    from twofa import (verify_totp, verify_backup_code, unused_backup_code_count,
                       webauthn_begin_authentication, webauthn_complete_authentication)
    user_id = session.get('pending_2fa_user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = dict_cursor(conn)
    cur.execute(
        'SELECT id, call_sign, email, is_admin, totp_secret, totp_enabled, webauthn_enabled '
        'FROM members WHERE id = %s', (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        session.pop('pending_2fa_user_id', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            flash('Please enter your verification code.', 'danger')
            return render_template('twofa/challenge.html', row=row)

        if row['totp_enabled'] and row['totp_secret'] and len(code) == 6 and code.isdigit():
            if verify_totp(row['totp_secret'], code):
                return _complete_2fa(row)
            flash('Invalid code. Please try again.', 'danger')
            return render_template('twofa/challenge.html', row=row)

        if verify_backup_code(user_id, code):
            remaining = unused_backup_code_count(user_id)
            resp = _complete_2fa(row)
            if remaining <= 2:
                flash(
                    f'Backup code accepted. You have {remaining} code(s) remaining — '
                    'consider regenerating them in your security settings.',
                    'warning',
                )
            else:
                flash('Backup code accepted.', 'success')
            return resp

        flash('Invalid code. Please try again.', 'danger')

    return render_template('twofa/challenge.html', row=row)


def _complete_2fa(row):
    next_url = _safe_redirect_url(session.pop('pending_2fa_next', None))
    # Regenerate session to prevent fixation: preserve nothing from pre-auth session
    session.clear()
    user = User(row['id'], row['call_sign'], row['email'], row['is_admin'])
    login_user(user, remember=True)
    return redirect(next_url)


@app.route('/2fa/webauthn/authenticate/begin', methods=['POST'])
def twofa_webauthn_auth_begin():
    from twofa import webauthn_begin_authentication
    user_id = session.get('pending_2fa_user_id')
    if not user_id:
        return jsonify({'error': 'No pending login'}), 400
    options_json, challenge_b64 = webauthn_begin_authentication(app, user_id)
    session['webauthn_auth_challenge'] = challenge_b64
    return options_json, 200, {'Content-Type': 'application/json'}


@app.route('/2fa/webauthn/authenticate/complete', methods=['POST'])
def twofa_webauthn_auth_complete():
    from twofa import webauthn_complete_authentication
    user_id = session.get('pending_2fa_user_id')
    challenge_b64 = session.pop('webauthn_auth_challenge', None)
    if not user_id or not challenge_b64:
        return jsonify({'success': False, 'message': 'Session expired'}), 400

    try:
        verified_user_id = webauthn_complete_authentication(app, challenge_b64, request.get_json(force=True))
    except Exception as e:
        app.logger.warning('WebAuthn authentication failed: %s', e)
        return jsonify({'success': False, 'message': 'Security key verification failed'}), 400

    if verified_user_id != user_id:
        return jsonify({'success': False, 'message': 'Key does not match account'}), 400

    conn = get_db_connection()
    cur = dict_cursor(conn)
    cur.execute('SELECT id, call_sign, email, is_admin FROM members WHERE id = %s', (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    next_url = _safe_redirect_url(session.pop('pending_2fa_next', None))
    session.clear()
    user = User(row['id'], row['call_sign'], row['email'], row['is_admin'])
    login_user(user, remember=True)
    return jsonify({'success': True, 'redirect': next_url})


@app.route('/2fa/setup/totp', methods=['GET', 'POST'])
@login_required
def twofa_setup_totp():
    from twofa import generate_totp_secret, get_totp_uri, verify_totp, generate_backup_codes
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'generate':
            secret = generate_totp_secret()
            session['totp_pending_secret'] = secret
            return render_template('twofa/setup_totp.html', secret=secret,
                                   uri=get_totp_uri(secret, current_user.username))

        if action == 'verify':
            secret = session.get('totp_pending_secret')
            code = request.form.get('code', '').strip()
            if not secret:
                flash('Session expired — please start over.', 'danger')
                return render_template('twofa/setup_totp.html')
            if not verify_totp(secret, code):
                flash('Incorrect code. Scan the QR code and try again.', 'danger')
                return render_template('twofa/setup_totp.html', secret=secret,
                                       uri=get_totp_uri(secret, current_user.username))
            conn = get_db_connection()
            cur = dict_cursor(conn)
            cur.execute(
                'UPDATE members SET totp_secret = %s, totp_enabled = 1 WHERE id = %s',
                (secret, current_user.id),
            )
            conn.commit()
            cur.close()
            conn.close()
            session.pop('totp_pending_secret', None)
            codes = generate_backup_codes(current_user.id)
            flash('Authenticator app linked successfully.', 'success')
            return render_template('twofa/backup_codes.html', codes=codes, just_generated=True)

    return render_template('twofa/setup_totp.html')


@app.route('/2fa/setup/totp/qr.png')
@login_required
def twofa_totp_qr():
    from twofa import generate_qr_png, get_totp_uri
    secret = session.get('totp_pending_secret')
    if not secret:
        abort(404)
    png = generate_qr_png(get_totp_uri(secret, current_user.username))
    return send_file(io.BytesIO(png), mimetype='image/png')


@app.route('/2fa/backup-codes', methods=['GET', 'POST'])
@login_required
def twofa_backup_codes():
    from twofa import generate_backup_codes, unused_backup_code_count
    if request.method == 'POST':
        pw = request.form.get('password', '')
        conn = get_db_connection()
        cur = dict_cursor(conn)
        cur.execute('SELECT password_hash FROM members WHERE id = %s', (current_user.id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not check_password(pw, row['password_hash']):
            flash('Incorrect password.', 'danger')
            return render_template('twofa/backup_codes.html',
                                   remaining=unused_backup_code_count(current_user.id))
        codes = generate_backup_codes(current_user.id)
        return render_template('twofa/backup_codes.html', codes=codes, just_generated=True)

    return render_template('twofa/backup_codes.html',
                           remaining=unused_backup_code_count(current_user.id))


@app.route('/2fa/disable', methods=['POST'])
@login_required
def twofa_disable():
    pw = request.form.get('password', '')
    conn = get_db_connection()
    cur = dict_cursor(conn)
    cur.execute('SELECT password_hash FROM members WHERE id = %s', (current_user.id,))
    row = cur.fetchone()
    if not check_password(pw, row['password_hash']):
        cur.close()
        conn.close()
        flash('Incorrect password — 2FA not disabled.', 'danger')
        return redirect(url_for('twofa_security'))

    cur.execute(
        'UPDATE members SET totp_secret = NULL, totp_enabled = 0, webauthn_enabled = 0 WHERE id = %s',
        (current_user.id,),
    )
    cur.execute('DELETE FROM totp_backup_codes WHERE user_id = %s', (current_user.id,))
    cur.execute('DELETE FROM webauthn_credentials WHERE user_id = %s', (current_user.id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('Two-factor authentication has been disabled.', 'success')
    return redirect(url_for('twofa_security'))


@app.route('/2fa/setup/webauthn', methods=['GET', 'POST'])
@login_required
def twofa_setup_webauthn():
    if request.method == 'POST':
        key_name = request.form.get('key_name', 'Security Key').strip() or 'Security Key'
        session['webauthn_reg_key_name'] = key_name
        return render_template('twofa/webauthn_register.html', key_name=key_name)
    return render_template('twofa/webauthn_register.html')


@app.route('/2fa/webauthn/register/begin', methods=['POST'])
@login_required
def twofa_webauthn_reg_begin():
    from twofa import webauthn_begin_registration
    options_json, challenge_b64 = webauthn_begin_registration(app, current_user)
    session['webauthn_reg_challenge'] = challenge_b64
    return options_json, 200, {'Content-Type': 'application/json'}


@app.route('/2fa/webauthn/register/complete', methods=['POST'])
@login_required
def twofa_webauthn_reg_complete():
    from twofa import webauthn_complete_registration
    challenge_b64 = session.pop('webauthn_reg_challenge', None)
    if not challenge_b64:
        return jsonify({'success': False, 'message': 'Session expired'}), 400

    key_name = session.pop('webauthn_reg_key_name', 'Security Key')
    try:
        webauthn_complete_registration(app, challenge_b64, request.get_json(force=True),
                                       current_user.id, key_name)
    except Exception as e:
        app.logger.warning('WebAuthn registration failed: %s', e)
        return jsonify({'success': False, 'message': 'Security key registration failed'}), 400

    return jsonify({'success': True, 'redirect': url_for('twofa_security')})


@app.route('/2fa/webauthn/delete/<int:cred_id>', methods=['POST'])
@login_required
def twofa_webauthn_delete(cred_id):
    from twofa import delete_webauthn_credential
    delete_webauthn_credential(cred_id, current_user.id)
    flash('Security key removed.', 'success')
    return redirect(url_for('twofa_security'))


@app.route('/2fa/security')
@login_required
def twofa_security():
    from twofa import get_webauthn_credentials, unused_backup_code_count
    conn = get_db_connection()
    cur = dict_cursor(conn)
    cur.execute('SELECT totp_enabled, webauthn_enabled FROM members WHERE id = %s', (current_user.id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    keys = get_webauthn_credentials(current_user.id)
    remaining = unused_backup_code_count(current_user.id) if row['totp_enabled'] else 0
    return render_template('twofa/security.html', row=row, keys=keys, remaining=remaining)


# ---------------------------------------------------------------
# Demo reset endpoint
# ---------------------------------------------------------------

@app.route('/demo/reset', methods=['POST'])
@csrf.exempt
def demo_reset():
    if not DEMO_MODE:
        abort(404)

    token    = request.args.get('token') or request.form.get('token')
    is_admin = current_user.is_authenticated and current_user.is_admin
    if not is_admin and (not DEMO_RESET_TOKEN or not hmac.compare_digest(token or '', DEMO_RESET_TOKEN)):
        abort(403)

    seed_path = os.path.join(os.path.dirname(__file__), '..', 'demo', 'seed.sql')
    if not os.path.isfile(seed_path):
        abort(404)
    sql = open(seed_path).read()

    clean = '\n'.join(
        ln for ln in sql.splitlines()
        if ln.strip() and not ln.strip().startswith('--')
    )
    conn = get_db_connection()
    cur  = conn.cursor()
    for stmt in clean.split(';\n'):
        stmt = stmt.strip().rstrip(';').strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'success': True, 'message': 'Demo data has been reset.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
