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

from .merit_list import (
    MERIT_EXPORT_HEADERS,
    STATUS_FILTER_CHOICES,
    build_merit_list_groups,
    build_merit_list_workbook,
    get_merit_program_choices,
    iter_merit_export_rows,
    merit_export_filename,
)


def _students_filter_params(request):
    """Read list filters from POST (actions) or GET (page load / filter form)."""
    if request.method == 'POST':
        source = request.POST
    else:
        source = request.GET

    program = (source.get('program') or 'ALL').strip() or 'ALL'
    verified = (source.get('verified') or 'ALL').strip() or 'ALL'
    return {
        'search': source.get('search', '').strip(),
        'program': program,
        'verified': verified,
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


def _export_course_name_only(label):
    """Strip B.Sc. department prefix; keep paper/course name only."""
    name = (label or '').strip()
    if not name:
        return ''
    if ' — ' in name:
        _department, course_name = name.split(' — ', 1)
        if course_name.strip():
            return course_name.strip()
    return name


def _format_selected_courses_for_export(student):
    """Paper names from the student's latest admission, for CSV export."""
    admission = getattr(student, 'latest_admission', None)
    if admission:
        subjects = parse_selected_subjects(admission)
        if subjects:
            names = [
                _export_course_name_only(s.get('name'))
                for s in subjects
                if isinstance(s, dict) and _export_course_name_only(s.get('name'))
            ]
            if names:
                return '; '.join(names)
        if (admission.subject or '').strip():
            names = [
                _export_course_name_only(part)
                for part in admission.subject.split(',')
                if _export_course_name_only(part)
            ]
            if names:
                return '; '.join(names)
    return _export_course_name_only(student.course_name)


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


def _program_group_label(program_type):
    label = (program_type or '').strip()
    return label or 'Not Assigned'


def _build_verified_students_by_program():
    """Group verified students by program (class) for admin dashboard."""
    verified = list(
        Student.objects.filter(is_verified=True).order_by('program_type', 'full_name', 'registration_no')
    )
    _attach_admissions(verified)

    groups = {}
    for student in verified:
        program = _program_group_label(student.program_type)
        groups.setdefault(program, []).append(student)

    return [
        {
            'program': program,
            'count': len(students),
            'students': students,
        }
        for program, students in sorted(
            groups.items(),
            key=lambda item: (item[0] == 'Not Assigned', item[0].lower()),
        )
    ]


_REJECTABLE_ADMISSION_STATUSES = ('Submitted', 'Pending', 'Approved')


def _get_latest_admission_for_student(student):
    return (
        StudentAdmission.objects.filter(reg_no=student.registration_no)
        .order_by('-submitted_date', '-created_date')
        .first()
    )


def _reject_student_application(student):
    admission = _get_latest_admission_for_student(student)
    if not admission or admission.status not in _REJECTABLE_ADMISSION_STATUSES:
        return False
    admission.status = 'Rejected'
    admission.save(update_fields=['status'])
    return True


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
    show_verified = request.GET.get('show_verified') == '1'
    verified_students = Student.objects.filter(is_verified=True).count()
    stats = {
        'total_admissions': StudentAdmission.objects.count(),
        'pending': StudentAdmission.objects.filter(status='Pending').count(),
        'approved': StudentAdmission.objects.filter(status='Approved').count(),
        'rejected': StudentAdmission.objects.filter(status='Rejected').count(),
        'submitted': StudentAdmission.objects.filter(status='Submitted').count(),
        'students': Student.objects.count(),
        'verified_students': verified_students,
    }
    recent = StudentAdmission.objects.order_by('-submitted_date', '-created_date')[:20]
    return render(request, 'admin_panel/dashboard.html', {
        'stats': stats,
        'recent': recent,
        'show_verified': show_verified,
        'verified_by_program': _build_verified_students_by_program() if show_verified else [],
    })


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
    reset_password_display = request.session.pop('reset_password_display', None)
    bulk_reset_passwords_display = request.session.pop('bulk_reset_passwords_display', None)

    return render(request, 'admin_panel/students.html', {
        'students': students,
        'search': search,
        'program_filter': program_filter,
        'verified_filter': verified_filter,
        'program_types': program_types,
        'edit_student': edit_student,
        'filter_params': params,
        'total_count': len(students),
        'reset_password_display': reset_password_display,
        'bulk_reset_passwords_display': bulk_reset_passwords_display,
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
            f'Cannot delete {student.registration_no} — reject the submitted application first.',
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
    request.session['reset_password_display'] = {
        'registration_no': student.registration_no,
        'password': new_password,
    }
    messages.success(request, f'Password reset for {student.registration_no}.')
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
@require_http_methods(['POST'])
def bulk_student_action(request):
    valid_actions = ('verify', 'unverify', 'reset_password', 'reject_application', 'delete')
    params = _students_filter_params(request)
    raw_ids = request.POST.getlist('student_ids')
    student_ids = []
    for raw_id in raw_ids:
        try:
            student_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    action = request.POST.get('action', '').strip()
    if not student_ids:
        messages.error(request, 'Select at least one student.')
        return redirect(_students_url(params))
    if action not in valid_actions:
        messages.error(request, 'Choose a valid action.')
        return redirect(_students_url(params))

    students = list(Student.objects.filter(pk__in=student_ids))
    if not students:
        messages.error(request, 'No matching students found.')
        return redirect(_students_url(params))

    if action == 'verify':
        updated = Student.objects.filter(pk__in=student_ids).update(is_verified=True)
        messages.success(
            request,
            f'Marked {updated} student{"s" if updated != 1 else ""} as verified.',
        )
    elif action == 'unverify':
        updated = Student.objects.filter(pk__in=student_ids).update(is_verified=False)
        messages.success(
            request,
            f'Marked {updated} student{"s" if updated != 1 else ""} as not verified.',
        )
    elif action == 'reset_password':
        reset_list = []
        for student in students:
            new_password = generate_secure_password()
            student.password = new_password
            student.save(update_fields=['password'])
            reset_list.append({
                'registration_no': student.registration_no,
                'password': new_password,
            })
        request.session['bulk_reset_passwords_display'] = reset_list
        messages.success(
            request,
            f'Reset password for {len(reset_list)} student{"s" if len(reset_list) != 1 else ""}.',
        )
    elif action == 'reject_application':
        rejected = 0
        skipped = []
        for student in students:
            if _reject_student_application(student):
                rejected += 1
            else:
                skipped.append(student.registration_no)
        if rejected:
            messages.success(
                request,
                f'Rejected {rejected} application{"s" if rejected != 1 else ""}. '
                'Those students can now be deleted.',
            )
        if skipped:
            messages.warning(
                request,
                'Skipped '
                f'{len(skipped)} student{"s" if len(skipped) != 1 else ""} with no rejectable application: '
                + ', '.join(skipped),
            )
        if not rejected and not skipped:
            messages.error(request, 'No applications were rejected.')
    elif action == 'delete':
        deleted = 0
        skipped = []
        for student in students:
            if StudentAdmission.objects.filter(
                reg_no=student.registration_no,
                status='Submitted',
            ).exists():
                skipped.append(student.registration_no)
                continue
            reg_no = student.registration_no
            StudentAdmission.objects.filter(reg_no=reg_no).delete()
            student.delete()
            deleted += 1
        if deleted:
            messages.success(
                request,
                f'Deleted {deleted} student{"s" if deleted != 1 else ""}.',
            )
        if skipped:
            messages.warning(
                request,
                'Skipped '
                f'{len(skipped)} student{"s" if len(skipped) != 1 else ""} with submitted applications '
                '(reject the application first): '
                + ', '.join(skipped),
            )
        if not deleted and not skipped:
            messages.error(request, 'No students were deleted.')

    return redirect(_students_url(params))


def _merit_list_params(request):
    program = request.GET.get('program', 'ALL').strip() or 'ALL'
    status = request.GET.get('status', 'applied').strip() or 'applied'
    valid_statuses = {key for key, _ in STATUS_FILTER_CHOICES}
    if status not in valid_statuses:
        status = 'applied'
    return {'program': program, 'status': status}


@admin_login_required
def merit_list(request):
    params = _merit_list_params(request)
    program_filter = params['program']
    status_filter = params['status']
    groups = build_merit_list_groups(program_filter, status_filter)
    total_applications = sum(group['count'] for group in groups)

    return render(request, 'admin_panel/merit_list.html', {
        'groups': groups,
        'program_filter': program_filter,
        'status_filter': status_filter,
        'program_choices': get_merit_program_choices(status_filter),
        'status_choices': STATUS_FILTER_CHOICES,
        'total_applications': total_applications,
    })


@admin_login_required
def export_merit_list_csv(request):
    params = _merit_list_params(request)
    groups = build_merit_list_groups(params['program'], params['status'])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{merit_export_filename(params["program"], "csv")}"'
    )
    writer = csv.writer(response)
    writer.writerow(MERIT_EXPORT_HEADERS)
    for row in iter_merit_export_rows(groups):
        writer.writerow(row)
    return response


@admin_login_required
def export_merit_list_excel(request):
    params = _merit_list_params(request)
    groups = build_merit_list_groups(params['program'], params['status'])
    workbook = build_merit_list_workbook(
        groups,
        program_filter=params['program'],
        status_filter=params['status'],
    )

    response = HttpResponse(
        workbook.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{merit_export_filename(params["program"], "xlsx")}"'
    )
    return response


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


@admin_login_required
@require_http_methods(['POST'])
def bulk_update_admission_status(request):
    valid_statuses = ('Approved', 'Rejected', 'Pending', 'Submitted')
    raw_ids = request.POST.getlist('admission_ids')
    admission_ids = []
    for raw_id in raw_ids:
        try:
            admission_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    new_status = request.POST.get('status', '').strip()
    if not admission_ids:
        messages.error(request, 'Select at least one application.')
        return redirect('admin_dashboard')
    if new_status not in valid_statuses:
        messages.error(request, 'Choose a valid status.')
        return redirect('admin_dashboard')

    updated = StudentAdmission.objects.filter(pk__in=admission_ids).update(status=new_status)
    if updated:
        messages.success(
            request,
            f'Updated {updated} application{"s" if updated != 1 else ""} to {new_status}.',
        )
    else:
        messages.error(request, 'No matching applications found.')
    return redirect('admin_dashboard')