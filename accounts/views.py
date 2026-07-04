import json
import re
from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from courses.constants import PROGRAM_LEVEL_CHOICES
from courses.utils import get_programs_by_level

from .forms import HelpdeskIssueForm
from .models import HelpdeskOfficer, HelpdeskIssue, ImportantInstruction, Notice, PasswordResetOTP, Student
from .utils import (
    admin_login_required,
    generate_otp,
    generate_registration_no,
    generate_secure_password,
    hash_otp,
    is_valid_aadhaar,
    is_valid_email,
    is_valid_mobile,
    mask_aadhaar,
    send_otp_email,
    send_registration_email,
    student_login_required,
)


def _home_page_context():
    now = timezone.now()
    return {
        'important_instructions': ImportantInstruction.objects.filter(is_active=True).order_by(
            'sort_order', '-created_at'
        ),
        'notices': Notice.objects.filter(
            is_active=True,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        ).order_by('sort_order', '-created_at'),
    }


def home(request):
    return render(request, 'home.html', _home_page_context())


@require_http_methods(['GET', 'POST'])
def helpdesk(request):
    officers = HelpdeskOfficer.objects.filter(is_active=True).order_by('sort_order', 'name')
    initial = {}
    if request.session.get('is_logged_in'):
        initial = {
            'name': request.session.get('student_name', ''),
            'email': request.session.get('student_email', ''),
            'mobile': request.session.get('student_mobile', ''),
            'registration_no': request.session.get('reg_no', ''),
        }

    if request.method == 'POST':
        form = HelpdeskIssueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your issue has been submitted successfully. Our helpdesk team will contact you soon.',
            )
            return redirect('helpdesk')
    else:
        form = HelpdeskIssueForm(initial=initial)

    return render(request, 'accounts/helpdesk.html', {
        'officers': officers,
        'form': form,
    })


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.session.get('is_logged_in'):
        return redirect('student_dashboard')
    if request.method == 'POST':
        user_input = request.POST.get('user', '').strip()
        password = request.POST.get('password', '').strip()
        if not user_input or not password:
            messages.error(request, 'Please enter both Email/Mobile and Password.')
        else:
            student = Student.objects.filter(
                Q(email__iexact=user_input) | Q(mobile=user_input),
                password=password,
            ).first()
            if student:
                request.session['is_logged_in'] = True
                request.session['reg_no'] = student.registration_no
                request.session['student_name'] = student.full_name
                request.session['student_email'] = student.email
                request.session['student_mobile'] = student.mobile
                return redirect('student_dashboard')
            messages.error(request, 'Invalid login credentials.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    request.session.flush()
    return redirect('home')


REGISTRATION_PROGRAM_LEVEL_LABELS = {
    'UG': 'Under Graduate',
    'PG': 'Post Graduate',
    'Diploma': 'Diploma',
}


@require_http_methods(['GET', 'POST'])
def registration_view(request):
    programs_by_level = get_programs_by_level()
    program_level_choices = [
        {
            'value': level,
            'label': REGISTRATION_PROGRAM_LEVEL_LABELS.get(level, level),
        }
        for level in PROGRAM_LEVEL_CHOICES
    ]

    success_data = None
    selected_program_level = ''
    selected_program_name = ''

    if request.GET.get('success') and request.session.get('registration_no'):
        success_data = {
            'reg_no': request.session.pop('registration_no', ''),
            'password': request.session.pop('temp_password', ''),
        }

    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        middle = request.POST.get('middle_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        full_name = ' '.join(p for p in [first, middle, last] if p)
        email = request.POST.get('email', '').strip().lower()
        mobile = re.sub(r'\D', '', request.POST.get('mobile', '').strip())
        aadhaar = re.sub(r'\D', '', request.POST.get('aadhaar', '').strip())
        selected_program_level = request.POST.get('program_level', '').strip()
        selected_program_name = request.POST.get('program_name', '').strip()
        program_type = selected_program_name

        errors = []
        if not selected_program_level:
            errors.append('Please select Program Type.')
        elif selected_program_level not in PROGRAM_LEVEL_CHOICES:
            errors.append('Invalid Program Type selected.')
        if not selected_program_name:
            errors.append('Please select Program Name.')
        elif selected_program_name not in programs_by_level.get(selected_program_level, []):
            errors.append('Selected Program Name does not match the chosen Program Type.')
        if not full_name:
            errors.append('Name is required.')
        if not is_valid_email(email):
            errors.append('Invalid Email format.')
        if not is_valid_mobile(mobile):
            errors.append('Invalid Mobile Number. Must be 10 digits starting with 6-9.')
        if not is_valid_aadhaar(aadhaar):
            errors.append('Invalid Aadhaar Number. Must be exactly 12 digits.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            exists = Student.objects.filter(
                Q(email__iexact=email) | Q(mobile=mobile) | Q(aadhaar=aadhaar)
            ).exists()
            if exists:
                messages.error(request, 'Already registered with this Email, Mobile, or Aadhaar.')
            else:
                password = generate_secure_password()
                reg_no = generate_registration_no(program_type)
                Student.objects.create(
                    registration_no=reg_no,
                    full_name=full_name,
                    email=email,
                    mobile=mobile,
                    password=password,
                    aadhaar=aadhaar,
                    program_type=program_type,
                    created_date=timezone.now(),
                )
                send_registration_email(email, full_name, reg_no, password)
                request.session['registration_no'] = reg_no
                request.session['temp_password'] = password
                return redirect('/register/?success=1')

    return render(request, 'accounts/registration.html', {
        'program_level_choices': program_level_choices,
        'programs_by_level_json': json.dumps(programs_by_level),
        'selected_program_level': selected_program_level,
        'selected_program_name': selected_program_name,
        'success_data': success_data,
    })


@student_login_required
def student_dashboard(request):
    reg_no = request.session.get('reg_no')
    student = Student.objects.filter(registration_no=reg_no).first()
    if not student:
        messages.error(request, 'Student record not found.')
        return redirect('login')

    from admissions.services import (
        get_editable_admission,
        get_printable_admission,
        get_program_display_name,
        parse_selected_subjects,
    )

    admission = get_printable_admission(reg_no) or get_editable_admission(reg_no)
    selected_subjects = parse_selected_subjects(admission) if admission else []
    program_display = ''
    if admission and admission.program_type:
        program_display = get_program_display_name(admission)
    elif student.program_type:
        program_display = student.program_type
    else:
        program_display = 'Not Selected'

    courses_display = ''
    if admission and admission.subject:
        courses_display = admission.subject
    elif selected_subjects:
        courses_display = ', '.join(
            s.get('name', '') for s in selected_subjects if isinstance(s, dict) and s.get('name')
        )

    from .utils import get_student_sidebar_context

    ctx = {
        'student': student,
        'admission': admission,
        'masked_aadhaar': mask_aadhaar(student.aadhaar),
        'program_display': program_display,
        'selected_subjects': selected_subjects,
        'courses_display': courses_display,
    }
    ctx.update(get_student_sidebar_context(reg_no, active='dashboard'))
    return render(request, 'accounts/student_dashboard.html', ctx)


_RESET_SESSION_KEYS = ('reset_email', 'reset_step', 'otp_verified')


def _clear_reset_session(request):
    for key in _RESET_SESSION_KEYS:
        request.session.pop(key, None)


def _forgot_password_redirect(step='find'):
    if step == 'find':
        return redirect('forgot_password')
    return redirect(f'{reverse("forgot_password")}?step={step}')


def _otp_failure_message(reason):
    messages_by_reason = {
        'not_configured': (
            'Could not send OTP email. Email service is not configured correctly. '
            'Please contact the college office.'
        ),
        'daily_limit': (
            'The college email account has reached its daily sending limit. '
            'Please try again after 24 hours or contact the college office.'
        ),
        'auth_error': (
            'Could not send OTP email because the college email login failed. '
            'Please contact the college office.'
        ),
        'ses_not_verified': (
            'Could not send OTP because the email address is not verified with the mail service. '
            'Please contact the college office.'
        ),
        'ses_permission': (
            'Could not send OTP because the server is not allowed to send email. '
            'Please contact the college office.'
        ),
        'connection_error': (
            'Could not reach the email server right now. Please try again later.'
        ),
    }
    return messages_by_reason.get(
        reason,
        'Could not send OTP email right now. Please try again later or contact the college office.',
    )


def _send_password_reset_otp(request, email):
    otp = generate_otp()
    PasswordResetOTP.objects.create(
        email=email,
        otp_hash=hash_otp(otp),
        expiry_at=timezone.now() + timedelta(minutes=10),
    )
    sent, reason = send_otp_email(email, otp)
    if sent:
        request.session['reset_email'] = email
        request.session['reset_step'] = 'verify'
        return True, reason
    return False, reason


@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    step = 'find'
    reset_email = None

    if request.method == 'GET':
        step_param = request.GET.get('step')
        if step_param in ('verify', 'reset'):
            reset_email = request.session.get('reset_email')
            session_step = request.session.get('reset_step', 'find')
            if step_param == 'verify' and reset_email and session_step == 'verify':
                step = 'verify'
            elif (
                step_param == 'reset'
                and reset_email
                and session_step == 'reset'
                and request.session.get('otp_verified')
            ):
                step = 'reset'
            else:
                _clear_reset_session(request)
        else:
            _clear_reset_session(request)

    if request.method == 'POST':
        action = request.POST.get('action', 'find')

        if action == 'find':
            email = request.POST.get('email', '').strip().lower()
            if not is_valid_email(email):
                messages.error(request, 'Please enter a valid email address.')
                return _forgot_password_redirect()

            student = Student.objects.filter(email__iexact=email).first()
            if student:
                sent, reason = _send_password_reset_otp(request, student.email)
                if sent:
                    messages.success(
                        request,
                        'OTP has been sent to your registered email. Check your inbox.',
                    )
                    return _forgot_password_redirect('verify')
                messages.error(request, _otp_failure_message(reason))
                return _forgot_password_redirect()
            messages.error(
                request,
                'No account found with this email. Use the same email you used during registration.',
            )
            return _forgot_password_redirect()

        if action in ('send_otp', 'resend_otp'):
            email = request.session.get('reset_email')
            if not email:
                return _forgot_password_redirect()
            sent, reason = _send_password_reset_otp(request, email)
            if sent:
                messages.info(request, 'A new OTP has been sent to your registered email.')
                return _forgot_password_redirect('verify')
            messages.error(request, _otp_failure_message(reason))
            return _forgot_password_redirect()

        if action == 'verify_otp':
            email = request.session.get('reset_email')
            if not email:
                return _forgot_password_redirect()
            otp_input = request.POST.get('otp', '').strip()
            record = (
                PasswordResetOTP.objects.filter(email=email, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if not record or record.expiry_at < timezone.now():
                messages.error(request, 'OTP expired. Please request a new one.')
                return _forgot_password_redirect('verify')
            if record.otp_hash != hash_otp(otp_input):
                record.attempts += 1
                record.save(update_fields=['attempts'])
                messages.error(request, 'Invalid OTP.')
                return _forgot_password_redirect('verify')
            record.is_used = True
            record.save(update_fields=['is_used'])
            request.session['otp_verified'] = True
            request.session['reset_step'] = 'reset'
            messages.success(request, 'OTP verified.')
            return _forgot_password_redirect('reset')

        if action == 'reset_password':
            if not request.session.get('otp_verified'):
                return _forgot_password_redirect()
            new_pass = request.POST.get('new_password', '').strip()
            confirm = request.POST.get('confirm_password', '').strip()
            if not new_pass or new_pass != confirm:
                messages.error(request, 'Passwords do not match.')
                return _forgot_password_redirect('reset')
            email = request.session.get('reset_email')
            Student.objects.filter(email__iexact=email).update(password=new_pass)
            _clear_reset_session(request)
            messages.success(request, 'Password reset successful. Please login.')
            return redirect('login')

    if step != 'find':
        reset_email = request.session.get('reset_email')

    return render(request, 'accounts/forgot_password.html', {
        'step': step,
        'reset_email': reset_email,
    })