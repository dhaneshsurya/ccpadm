import hashlib
import logging
import random
import re
import secrets
import smtplib
from datetime import timedelta

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

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


def is_email_configured():
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def classify_smtp_failure(exc: Exception) -> str:
    """Map SMTP exceptions to stable failure codes for user messaging."""
    raw = exc
    if hasattr(exc, 'smtp_error'):
        smtp_error = exc.smtp_error
        if isinstance(smtp_error, bytes):
            raw = smtp_error.decode('utf-8', errors='replace')
        else:
            raw = str(smtp_error)
    text = f'{exc} {raw}'.lower()

    if 'daily user sending limit' in text or 'sending limit exceeded' in text:
        return 'daily_limit'
    if 'username and password not accepted' in text or 'authentication failed' in text:
        return 'auth_error'
    if 'connection refused' in text or 'timed out' in text or 'network is unreachable' in text:
        return 'connection_error'
    return 'smtp_error'


def send_registration_email(email, name, reg_no, password):
    if not email or not is_email_configured():
        return
    body = (
        f'Hello {name},\n\n'
        f'Your registration is complete.\n'
        f'Registration Number: {reg_no}\n'
        f'Temporary Password: {password}\n\n'
        f'Please keep this information safe.'
    )
    send_mail(
        'Registration Successful - Chaitanya College',
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=True,
    )


def send_otp_email(email, otp):
    """Send OTP email. Returns (success, failure_reason)."""
    if not email:
        return False, 'missing_email'

    subject = 'Password Reset OTP - Chaitanya College'
    body = f'Your OTP is: {otp}\nValid for 10 minutes.'

    if not is_email_configured():
        if settings.DEBUG:
            logger.warning('EMAIL not configured. OTP for %s: %s', email, otp)
            return True, 'debug_fallback'
        logger.error(
            'Email SMTP is not configured (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD); cannot send OTP to %s',
            email,
        )
        return False, 'not_configured'

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True, 'sent'
    except (smtplib.SMTPException, OSError) as exc:
        reason = classify_smtp_failure(exc)
        logger.error('Failed to send OTP email to %s (%s): %s', email, reason, exc)
        return False, reason
    except Exception:
        logger.exception('Failed to send OTP email to %s', email)
        return False, 'smtp_error'


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