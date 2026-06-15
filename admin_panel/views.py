import csv
import re

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import AdminUser, Student
from accounts.utils import (
    admin_login_required,
    generate_secure_password,
    is_valid_aadhaar,
    is_valid_email,
    is_valid_mobile,
)
from admissions.models import StudentAdmission
from admissions.services import get_print_context, parse_selected_subjects
from courses.utils import get_program_names


def _students_filter_params(request):
    return {
        'search': request.GET.get('search', '').strip() or request.POST.get('search', '').strip(),
        'program': request.GET.get('program', 'ALL').strip() or request.POST.get('program', 'ALL').strip(),
        'verified': request.GET.get('verified', 'ALL').strip() or request.POST.get('verified', 'ALL').strip(),
    }


def _students_url(params=None, edit_pk=None):
    from urllib.parse import urlencode
    from django.urls import reverse

    query = dict(params or {})
    if edit_pk:
        query['edit'] = edit_pk
    base = reverse('manage_students')
    if not query:
        return base
    return f'{base}?{urlencode(query)}'


def _get_students_queryset(search='', program_filter='ALL', verified_filter='ALL'):
    students = Student.objects.all()
    if search:
        students = students.filter(
            Q(full_name__icontains=search)
            | Q(email__icontains=search)
            | Q(mobile__icontains=search)
            | Q(registration_no__icontains=search)
            | Q(aadhaar__icontains=search)
        )
    if program_filter != 'ALL':
        students = students.filter(program_type=program_filter)
    if verified_filter == 'YES':
        students = students.filter(is_verified=True)
    elif verified_filter == 'NO':
        students = students.filter(is_verified=False)
    return students.order_by('-created_date')


def _format_selected_courses_for_export(student):
    """Paper names from the student's latest admission, for CSV export."""
    admission = getattr(student, 'latest_admission', None)
    if admission:
        subjects = parse_selected_subjects(admission)
        if subjects:
            names = [
                (s.get('name') or '').strip()
                for s in subjects
                if isinstance(s, dict) and (s.get('name') or '').strip()
            ]
            if names:
                return '; '.join(names)
        if (admission.subject or '').strip():
            return admission.subject.strip()
    return (student.course_name or '').strip()


def _attach_admissions(students):
    reg_nos = [s.registration_no for s in students]
    admission_map = {}
    if reg_nos:
        for adm in (
            StudentAdmission.objects.filter(reg_no__in=reg_nos)
            .order_by('-submitted_date', '-created_date')
        ):
            if adm.reg_no not in admission_map:
                admission_map[adm.reg_no] = adm
    for student in students:
        student.latest_admission = admission_map.get(student.registration_no)
    return students


def _validate_student_form(post, student=None):
    errors = []
    full_name = post.get('full_name', '').strip()
    email = post.get('email', '').strip().lower()
    mobile = re.sub(r'\D', '', post.get('mobile', '').strip())
    aadhaar = re.sub(r'\D', '', post.get('aadhaar', '').strip())
    program_type = post.get('program_type', '').strip()

    if not full_name:
        errors.append('Full name is required.')
    if email and not is_valid_email(email):
        errors.append('Invalid email format.')
    if mobile and not is_valid_mobile(mobile):
        errors.append('Invalid mobile number.')
    if aadhaar and not is_valid_aadhaar(aadhaar):
        errors.append('Invalid Aadhaar number.')

    if email:
        qs = Student.objects.filter(email__iexact=email)
        if student:
            qs = qs.exclude(pk=student.pk)
        if qs.exists():
            errors.append('Another student already uses this email.')

    if mobile:
        qs = Student.objects.filter(mobile=mobile)
        if student:
            qs = qs.exclude(pk=student.pk)
        if qs.exists():
            errors.append('Another student already uses this mobile.')

    if aadhaar:
        qs = Student.objects.filter(aadhaar=aadhaar)
        if student:
            qs = qs.exclude(pk=student.pk)
        if qs.exists():
            errors.append('Another student already uses this Aadhaar.')

    return errors, {
        'full_name': full_name,
        'email': email,
        'mobile': mobile,
        'aadhaar': aadhaar,
        'program_type': program_type,
        'course_name': post.get('course_name', '').strip(),
        'is_verified': post.get('is_verified') == 'on',
    }


@require_http_methods(['GET', 'POST'])
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if AdminUser.objects.filter(username=username, password=password).exists():
            request.session['admin_user'] = username
            return redirect('admin_dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    request.session.pop('admin_user', None)
    return redirect('admin_login')


@admin_login_required
def admin_dashboard(request):
    stats = {
        'total_admissions': StudentAdmission.objects.count(),
        'pending': StudentAdmission.objects.filter(status='Pending').count(),
        'approved': StudentAdmission.objects.filter(status='Approved').count(),
        'rejected': StudentAdmission.objects.filter(status='Rejected').count(),
        'submitted': StudentAdmission.objects.filter(status='Submitted').count(),
        'students': Student.objects.count(),
    }
    recent = StudentAdmission.objects.order_by('-submitted_date', '-created_date')[:20]
    return render(request, 'admin_panel/dashboard.html', {'stats': stats, 'recent': recent})


@admin_login_required
def manage_students(request):
    params = _students_filter_params(request)
    search = params['search']
    program_filter = params['program']
    verified_filter = params['verified']
    edit_pk = request.GET.get('edit', '').strip()

    students = _attach_admissions(
        list(_get_students_queryset(search, program_filter, verified_filter))
    )

    edit_student = None
    if edit_pk:
        edit_student = Student.objects.filter(pk=edit_pk).first()
        if edit_student:
            _attach_admissions([edit_student])

    program_types = get_program_names(active_only=False)

    return render(request, 'admin_panel/students.html', {
        'students': students,
        'search': search,
        'program_filter': program_filter,
        'verified_filter': verified_filter,
        'program_types': program_types,
        'edit_student': edit_student,
        'filter_params': params,
        'total_count': len(students),
    })


@admin_login_required
@require_http_methods(['POST'])
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    errors, data = _validate_student_form(request.POST, student=student)
    params = _students_filter_params(request)

    if errors:
        for err in errors:
            messages.error(request, err)
        return redirect(_students_url(params, edit_pk=pk))

    student.full_name = data['full_name']
    student.email = data['email'] or None
    student.mobile = data['mobile'] or None
    student.aadhaar = data['aadhaar'] or None
    student.program_type = data['program_type']
    student.course_name = data['course_name']
    student.is_verified = data['is_verified']
    student.save()
    messages.success(request, f'Student {student.registration_no} updated successfully.')
    return redirect(_students_url(params))


@admin_login_required
@require_http_methods(['POST'])
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    params = _students_filter_params(request)

    if StudentAdmission.objects.filter(reg_no=student.registration_no, status='Submitted').exists():
        messages.error(
            request,
            f'Cannot delete {student.registration_no} — a submitted application exists.',
        )
        return redirect(_students_url(params))

    reg_no = student.registration_no
    StudentAdmission.objects.filter(reg_no=reg_no).delete()
    student.delete()
    messages.success(request, f'Student {reg_no} deleted.')
    return redirect(_students_url(params))


@admin_login_required
@require_http_methods(['POST'])
def reset_student_password(request, pk):
    student = get_object_or_404(Student, pk=pk)
    params = _students_filter_params(request)
    new_password = generate_secure_password()
    student.password = new_password
    student.save(update_fields=['password'])
    messages.success(
        request,
        f'Password reset for {student.registration_no}. New password: {new_password}',
    )
    return redirect(_students_url(params))


@admin_login_required
@require_http_methods(['POST'])
def toggle_student_verified(request, pk):
    student = get_object_or_404(Student, pk=pk)
    params = _students_filter_params(request)
    student.is_verified = not student.is_verified
    student.save(update_fields=['is_verified'])
    state = 'verified' if student.is_verified else 'unverified'
    messages.success(request, f'{student.registration_no} marked as {state}.')
    return redirect(_students_url(params))


@admin_login_required
def export_students_csv(request):
    params = _students_filter_params(request)
    students = _attach_admissions(
        _get_students_queryset(params['search'], params['program'], params['verified'])
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Registration No', 'Full Name', 'Email', 'Mobile', 'Aadhaar',
        'Program', 'Course', 'Selected Courses / Paper Name',
        'Application No', 'Verified', 'Registered On',
    ])
    for s in students:
        admission = getattr(s, 'latest_admission', None)
        writer.writerow([
            s.registration_no,
            s.full_name,
            s.email or '',
            s.mobile or '',
            s.aadhaar or '',
            s.program_type,
            s.course_name,
            _format_selected_courses_for_export(s),
            (admission.application_no if admission else '') or '',
            'Yes' if s.is_verified else 'No',
            s.created_date.strftime('%d-%m-%Y %H:%M') if s.created_date else '',
        ])
    return response


@admin_login_required
def admin_print_application(request, app_no):
    admission = get_object_or_404(StudentAdmission, application_no=app_no)
    context = get_print_context(admission)
    context['preview_mode'] = False
    context['admin_view'] = True
    return render(request, 'admissions/print_full.html', context)


@admin_login_required
def admin_download_pdf(request, app_no):
    from admissions.pdf import render_admission_pdf

    admission = get_object_or_404(StudentAdmission, application_no=app_no)
    pdf_bytes = render_admission_pdf(admission)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{app_no}.pdf"'
    return response


@admin_login_required
@require_http_methods(['POST'])
def update_admission_status(request, pk):
    admission = StudentAdmission.objects.filter(pk=pk).first()
    if not admission:
        messages.error(request, 'Admission not found.')
        return redirect('admin_dashboard')
    new_status = request.POST.get('status')
    if new_status in ('Approved', 'Rejected', 'Pending', 'Submitted'):
        admission.status = new_status
        admission.save(update_fields=['status'])
        messages.success(request, f'Status updated to {new_status}.')
    return redirect(request.POST.get('next', 'admin_dashboard'))