import hashlib
import html
import logging
import random
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .email_config import (
    get_public_site_url,
    is_email_configured,
    send_transactional_email,
)

logger = logging.getLogger(__name__)


def is_valid_email(email):
    if not email:
        return False
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email.strip()))


def is_valid_mobile(mobile):
    if not mobile:
        return False
    mobile = re.sub(r'\D', '', mobile)
    return len(mobile) == 10 and bool(re.match(r'^[6-9]\d{9}$', mobile))


def is_valid_aadhaar(aadhaar):
    if not aadhaar:
        return False
    aadhaar = re.sub(r'\D', '', aadhaar)
    return len(aadhaar) == 12 and aadhaar.isdigit()


def generate_secure_password(length=6):
    return str(random.randint(100000, 999999))


def generate_registration_no(program_type=''):
    from .models import Student

    prefix = 'AS' + timezone.now().strftime('%y%m')
    last = (
        Student.objects.filter(registration_no__startswith=prefix)
        .order_by('-registration_no')
        .values_list('registration_no', flat=True)
        .first()
    )
    if last and len(last) >= 4:
        try:
            seq = int(last[-4:]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'


def hash_otp(otp):
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


def send_registration_email(email, name, reg_no, password):
    """
    Send registration credentials. Returns True if delivered (or DEBUG fallback).
    Failures are logged; registration still succeeds so students can use on-screen credentials.
    """
    if not email:
        return False

    if not is_email_configured():
        if settings.DEBUG:
            logger.warning(
                'EMAIL not configured. Registration for %s: reg_no=%s password=%s',
                email,
                reg_no,
                password,
            )
            return True
        logger.error('Email not configured; cannot send registration mail to %s', email)
        return False

    site_url = get_public_site_url()
    login_url = f'{site_url}/login/'
    student_name = (name or 'Student').strip()
    student_name_html = html.escape(student_name)
    reg_no_html = html.escape(str(reg_no))
    password_html = html.escape(str(password))

    subject = 'Your Chaitanya College online admission account'
    text_body = (
        f'Dear {student_name},\n\n'
        f'Thank you for registering on the Chaitanya Science & Arts College '
        f'online admission portal.\n\n'
        f'Your account has been created successfully. Please use the details below '
        f'to sign in and complete your admission form:\n\n'
        f'  Registration Number : {reg_no}\n'
        f'  Temporary Password  : {password}\n'
        f'  Login page          : {login_url}\n\n'
        f'For security, change your password after first login if you wish, and do not '
        f'share these details with anyone.\n\n'
        f'If you did not register on this portal, please ignore this message or contact '
        f'the college office.\n\n'
        f'Regards,\n'
        f'Chaitanya Science & Arts College\n'
        f'{site_url}\n'
    )
    html_body = f"""\
<html><body style="font-family: Arial, sans-serif; color: #0f172a; line-height: 1.5;">
  <p>Dear {student_name_html},</p>
  <p>Thank you for registering on the <strong>Chaitanya Science &amp; Arts College</strong>
  online admission portal.</p>
  <p>Your account has been created successfully. Use the details below to sign in and
  complete your admission form:</p>
  <table cellpadding="6" style="border-collapse: collapse; background: #f8fafc; border: 1px solid #e2e8f0;">
    <tr><td><strong>Registration Number</strong></td><td>{reg_no_html}</td></tr>
    <tr><td><strong>Temporary Password</strong></td><td>{password_html}</td></tr>
    <tr><td><strong>Login page</strong></td><td><a href="{html.escape(login_url)}">{html.escape(login_url)}</a></td></tr>
  </table>
  <p style="font-size: 0.9em; color: #475569;">
    For security, do not share these details. If you did not register, ignore this email
    or contact the college office.
  </p>
  <p>Regards,<br>Chaitanya Science &amp; Arts College<br>
  <a href="{html.escape(site_url)}">{html.escape(site_url)}</a></p>
</body></html>
"""
    ok, reason = send_transactional_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        to_email=email,
    )
    if not ok:
        logger.error('Registration email not delivered to %s (reason=%s)', email, reason)
    return ok


def send_otp_email(email, otp):
    """Send OTP email. Returns (success, failure_reason)."""
    if not email:
        return False, 'missing_email'

    if not is_email_configured():
        if settings.DEBUG:
            logger.warning('EMAIL not configured. OTP for %s: %s', email, otp)
            return True, 'debug_fallback'
        logger.error(
            'Email is not configured (SES DEFAULT_FROM_EMAIL or SMTP credentials); cannot send OTP to %s',
            email,
        )
        return False, 'not_configured'

    site_url = get_public_site_url()
    subject = 'Password reset code — Chaitanya College admission portal'
    text_body = (
        f'Dear Student,\n\n'
        f'You requested a password reset for your Chaitanya Science & Arts College '
        f'online admission account.\n\n'
        f'Your one-time verification code is: {otp}\n'
        f'This code is valid for 10 minutes.\n\n'
        f'If you did not request a password reset, please ignore this email.\n\n'
        f'Regards,\n'
        f'Chaitanya Science & Arts College\n'
        f'{site_url}\n'
    )
    html_body = f"""\
<html><body style="font-family: Arial, sans-serif; color: #0f172a; line-height: 1.5;">
  <p>Dear Student,</p>
  <p>You requested a password reset for your
  <strong>Chaitanya Science &amp; Arts College</strong> online admission account.</p>
  <p style="font-size: 1.25rem; letter-spacing: 0.12em;"><strong>{otp}</strong></p>
  <p>This code is valid for <strong>10 minutes</strong>.</p>
  <p style="font-size: 0.9em; color: #475569;">
    If you did not request a password reset, please ignore this email.
  </p>
  <p>Regards,<br>Chaitanya Science &amp; Arts College<br>
  <a href="{site_url}">{site_url}</a></p>
</body></html>
"""
    return send_transactional_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        to_email=email,
    )


def mask_aadhaar(aadhaar):
    if not aadhaar:
        return 'Not Provided'
    clean = re.sub(r'[\s-]', '', aadhaar)
    if len(clean) < 4:
        return 'Invalid Aadhaar'
    if len(clean) == 12:
        return f'XXXX-XXXX-{clean[-4:]}'
    return f'XXXX-{clean[-4:]}'


def get_student_sidebar_context(reg_no, active=''):
    from admissions.services import get_editable_admission, get_printable_admission, is_admission_locked

    printable = get_printable_admission(reg_no)
    editable = get_editable_admission(reg_no)
    return {
        'sidebar_active': active,
        'admission_submitted': printable is not None,
        'admission_editable': editable is not None and not is_admission_locked(reg_no),
        'sidebar_app_no': printable.application_no if printable else '',
    }


def student_login_required(view_func):
    from functools import wraps
    from django.shortcuts import redirect

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_logged_in'):
            return redirect('login')
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_login_required(view_func):
    from functools import wraps
    from django.shortcuts import redirect

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_user'):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)

    return wrapper