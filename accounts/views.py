import re
from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from courses.utils import get_program_names

from .models import PasswordResetOTP, Student
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


def home(request):
    if request.session.get('is_logged_in'):
        return redirect('student_dashboard')
    return render(request, 'home.html')


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


@require_http_methods(['GET', 'POST'])
def registration_view(request):
    program_types = get_program_names()

    success_data = None
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
        program_type = request.POST.get('program_type', '')

        errors = []
        if not program_type:
            errors.append('Please select Program Type.')
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
        'program_types': program_types,
        'success_data': success_data,
    })


@student_login_required
def student_dashboard(request):
    reg_no = request.session.get('reg_no')
    student = Student.objects.filter(registration_no=reg_no).first()
    if not student:
        messages.error(request, 'Student record not found.')
        return redirect('login')

    from admissions.services import get_editable_admission, get_printable_admission, parse_selected_subjects

    admission = get_printable_admission(reg_no) or get_editable_admission(reg_no)
    selected_subjects = parse_selected_subjects(admission) if admission else []
    program_display = ''
    if admission and admission.program_type:
        program_display = admission.program_type
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


@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    program_types = get_program_names()
    found_user = request.session.get('reset_user')
    step = request.session.get('reset_step', 'find')

    if request.method == 'POST':
        action = request.POST.get('action', 'find')

        if action == 'find':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            program = request.POST.get('program_type', '')
            student = Student.objects.filter(
                full_name__iexact=name, email__iexact=email, program_type=program
            ).first()
            if student:
                request.session['reset_user'] = {
                    'name': student.full_name,
                    'email': student.email,
                    'course': student.course_name,
                }
                request.session['reset_email'] = student.email
                request.session['reset_step'] = 'choose'
                messages.success(request, 'Account found.')
            else:
                messages.error(request, 'Account not found.')
            return redirect('forgot_password')

        if action == 'send_otp':
            email = request.session.get('reset_email')
            if not email:
                return redirect('forgot_password')
            otp = generate_otp()
            PasswordResetOTP.objects.create(
                email=email,
                otp_hash=hash_otp(otp),
                expiry_at=timezone.now() + timedelta(minutes=10),
            )
            send_otp_email(email, otp)
            request.session['reset_step'] = 'verify'
            messages.info(request, 'OTP sent to your email.')
            return redirect('forgot_password')

        if action == 'verify_otp':
            email = request.session.get('reset_email')
            otp_input = request.POST.get('otp', '').strip()
            record = (
                PasswordResetOTP.objects.filter(email=email, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if not record or record.expiry_at < timezone.now():
                messages.error(request, 'OTP expired. Please request a new one.')
            elif record.otp_hash != hash_otp(otp_input):
                record.attempts += 1
                record.save(update_fields=['attempts'])
                messages.error(request, 'Invalid OTP.')
            else:
                record.is_used = True
                record.save(update_fields=['is_used'])
                request.session['otp_verified'] = True
                request.session['reset_step'] = 'reset'
                messages.success(request, 'OTP verified.')
            return redirect('forgot_password')

        if action == 'reset_password':
            if not request.session.get('otp_verified'):
                return redirect('forgot_password')
            new_pass = request.POST.get('new_password', '').strip()
            confirm = request.POST.get('confirm_password', '').strip()
            if not new_pass or new_pass != confirm:
                messages.error(request, 'Passwords do not match.')
            else:
                email = request.session.get('reset_email')
                Student.objects.filter(email__iexact=email).update(password=new_pass)
                for key in ('reset_user', 'reset_email', 'reset_step', 'otp_verified'):
                    request.session.pop(key, None)
                messages.success(request, 'Password reset successful. Please login.')
                return redirect('login')

    return render(request, 'accounts/forgot_password.html', {
        'program_types': program_types,
        'found_user': found_user,
        'step': step,
    })