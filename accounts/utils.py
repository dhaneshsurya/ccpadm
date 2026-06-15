import hashlib
import logging
import random
import re
import secrets
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


def send_registration_email(email, name, reg_no, password):
    if not email or not settings.EMAIL_HOST_USER:
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
    if not email:
        return False

    subject = 'Password Reset OTP - Chaitanya College'
    body = f'Your OTP is: {otp}\nValid for 10 minutes.'

    if not settings.EMAIL_HOST_USER:
        if settings.DEBUG:
            logger.warning('EMAIL not configured. OTP for %s: %s', email, otp)
            return True
        logger.error('EMAIL_HOST_USER is not configured; cannot send OTP to %s', email)
        return False

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception('Failed to send OTP email to %s', email)
        return False


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