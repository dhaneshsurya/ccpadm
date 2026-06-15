import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import Student
from accounts.utils import get_student_sidebar_context, student_login_required
from courses.models import ProgramCourse
from courses.subject_groups import (
    BSC_PROGRAM,
    course_is_group_course,
    course_is_group_dsc,
    course_is_program_compulsory,
    get_assigned_group_keys,
    get_bsc_subject_group_sections,
    is_bsc_program,
    normalize_department,
    normalize_program_type_for_display,
    resolve_bsc_courses_program_type,
)
from courses.constants import PROGRAM_LEVEL_CHOICES, PROGRAM_LEVEL_DISPLAY
from courses.utils import (
    get_program_level_for_name,
    get_program_names,
    get_programs_by_level,
)

from .constants import MEDIUM_CHOICES, RELIGION_CHOICES
from .models import StudentAdmission
from .pdf import render_admission_pdf
from .services import (
    admission_to_form_dict,
    build_submit_payload,
    get_application_print_view_context,
    get_editable_admission,
    get_printable_admission,
    is_admission_locked,
    normalize_form_payload,
    resolve_save_status,
)
from .utils import generate_application_number, save_admission_from_form


@student_login_required
def fill_admission_form(request):
    reg_no = request.session.get('reg_no')
    student = get_object_or_404(Student, registration_no=reg_no)
    submitted = StudentAdmission.objects.filter(reg_no=reg_no, status='Submitted').order_by('-submitted_date').first()
    editable = get_editable_admission(reg_no)

    program_types = get_program_names()

    draft_data = admission_to_form_dict(editable, student) if editable else {}
    if editable and editable.application_no:
        draft_data['ApplicationNo'] = editable.application_no
    elif not draft_data.get('ApplicationNo'):
        draft_data['ApplicationNo'] = ''

    selected_program_type = normalize_program_type_for_display(
        draft_data.get('ProgramType') or student.program_type,
        program_types,
    )
    selected_program_level = get_program_level_for_name(selected_program_type)
    if draft_data and selected_program_type:
        draft_data['ProgramType'] = selected_program_type
        draft_data['ProgramLevel'] = selected_program_level
    programs_by_level = get_programs_by_level()

    ctx = {
        'student': student,
        'submitted': submitted,
        'draft': editable,
        'draft_data': draft_data,
        'program_types': program_types,
        'selected_program_type': selected_program_type,
        'selected_program_level': selected_program_level,
        'programs_by_level': programs_by_level,
        'programs_by_level_json': json.dumps(programs_by_level),
        'program_level_choices': [
            {'value': level, 'label': PROGRAM_LEVEL_DISPLAY[level]}
            for level in PROGRAM_LEVEL_CHOICES
            if programs_by_level.get(level)
        ],
        'religion_choices': RELIGION_CHOICES,
        'medium_choices': MEDIUM_CHOICES,
        'form_disabled': is_admission_locked(reg_no),
        'bsc_subject_groups': get_bsc_subject_group_sections(selected_program_type),
        'bsc_program_name': BSC_PROGRAM,
        'bsc_program_names_json': json.dumps([pt for pt in program_types if is_bsc_program(pt)]),
        'initial_program_type': selected_program_type,
        'initial_program_level': selected_program_level,
    }
    ctx.update(get_student_sidebar_context(reg_no, active='form'))
    return render(request, 'admissions/fill_form.html', ctx)


@student_login_required
def courses_api(request):
    program_type = request.GET.get('program_type', '').strip()
    if not program_type:
        return JsonResponse({'courses': []})
    show_bsc = is_bsc_program(program_type)
    course_program_type = (
        resolve_bsc_courses_program_type(program_type) if show_bsc else program_type
    )
    courses = (
        ProgramCourse.objects.filter(program_type=course_program_type)
        .prefetch_related('subject_groups')
        .order_by('sort_order', 'course_name')
    )
    data = []
    for c in courses:
        label = c.course_name
        department = normalize_department(c.department)
        if department:
            label = f'{department} — {c.course_name}'
        is_group_course = course_is_group_course(c, program_type) if show_bsc else False
        is_group_dsc = course_is_group_dsc(c, program_type) if show_bsc else False
        is_compulsory = course_is_program_compulsory(c, program_type)
        data.append({
            'id': c.legacy_id or c.pk,
            'course_name': label,
            'department': department,
            'course_type_1': c.course_type_1 or '',
            'course_type_2': c.course_type_2 or 'N/A',
            'is_compulsory': is_compulsory,
            'is_group_course': is_group_course,
            'is_group_dsc': is_group_dsc,
            'is_dsc': (c.course_type_2 or '').strip().upper() == 'DSC',
            'group_keys': get_assigned_group_keys(c),
        })

    payload = {
        'courses': data,
        'program_type': program_type,
        'resolved_program_type': course_program_type,
    }
    if show_bsc:
        payload['subject_groups'] = get_bsc_subject_group_sections(program_type)
    response = JsonResponse(payload)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response


@student_login_required
@require_http_methods(['POST'])
def save_draft_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'ERROR', 'message': 'Invalid JSON'}, status=400)

    reg_no = request.session.get('reg_no')
    if not reg_no:
        return JsonResponse({'status': 'ERROR', 'message': 'Session expired'}, status=401)

    payload = normalize_form_payload(data)
    if not payload.get('full_name'):
        student = Student.objects.filter(registration_no=reg_no).first()
        if student and student.full_name:
            payload['full_name'] = student.full_name
    if not payload.get('full_name'):
        return JsonResponse({'status': 'ERROR', 'message': 'Full Name is required'})

    existing = get_editable_admission(reg_no)
    if existing and existing.application_no:
        payload['application_no'] = existing.application_no
    elif not payload.get('application_no'):
        payload['application_no'] = generate_application_number()

    save_status = resolve_save_status(reg_no, payload.get('application_no'))
    admission = save_admission_from_form(payload, reg_no, status=save_status)
    return JsonResponse({'status': 'DRAFT_SAVED', 'application_no': admission.application_no})


@student_login_required
def load_draft_api(request):
    reg_no = request.session.get('reg_no')
    if not reg_no:
        return JsonResponse({'status': 'ERROR', 'message': 'Session expired'}, status=401)

    app_no = request.GET.get('app_no', '').strip()
    editable = get_editable_admission(reg_no, app_no or None)
    if not editable:
        return JsonResponse({'status': 'OK', 'data': {}})

    student = Student.objects.filter(registration_no=reg_no).first()
    data = admission_to_form_dict(editable, student)
    if editable.application_no:
        data['ApplicationNo'] = editable.application_no
    program_types = get_program_names()
    normalized_program = normalize_program_type_for_display(
        data.get('ProgramType') or (student.program_type if student else ''),
        program_types,
    )
    if normalized_program:
        data['ProgramType'] = normalized_program
        data['ProgramLevel'] = get_program_level_for_name(normalized_program)
    return JsonResponse({
        'status': 'OK',
        'data': data,
        'application_no': editable.application_no or '',
    })


@student_login_required
def preview_application(request):
    reg_no = request.session.get('reg_no')
    app_no = request.GET.get('app_no', '').strip()
    admission = None
    if app_no:
        admission = StudentAdmission.objects.filter(application_no=app_no, reg_no=reg_no).first()
        if not admission:
            other = StudentAdmission.objects.filter(application_no=app_no).first()
            if other and other.reg_no != reg_no:
                messages.error(request, 'You cannot view this application.')
                return redirect('fill_admission_form')
    if not admission:
        admission = get_editable_admission(reg_no)
    if not admission:
        messages.error(request, 'No application found. Please fill the admission form first.')
        return redirect('fill_admission_form')

    return render(
        request,
        'admissions/print_full.html',
        get_application_print_view_context(admission, preview_mode=True),
    )


@student_login_required
@require_http_methods(['POST'])
def submit_application(request):
    reg_no = request.session.get('reg_no')

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    app_no = data.get('application_no') or data.get('ApplicationNo')
    existing_submitted = StudentAdmission.objects.filter(reg_no=reg_no, status='Submitted').first()
    if existing_submitted and existing_submitted.application_no != app_no:
        return JsonResponse({'status': 'ERROR', 'message': 'Application already submitted'}, status=400)

    payload, draft = build_submit_payload(reg_no, data, generate_application_number)
    if not draft and not payload.get('full_name'):
        return JsonResponse({'status': 'ERROR', 'message': 'No application data found'}, status=400)
    if not payload.get('full_name'):
        student = Student.objects.filter(registration_no=reg_no).first()
        if student and student.full_name:
            payload['full_name'] = student.full_name

    admission = save_admission_from_form(payload, reg_no, status='Submitted')
    request.session['last_app_no'] = admission.application_no
    messages.success(request, f'Application submitted! App No: {admission.application_no}')
    return JsonResponse({
        'status': 'SUCCESS',
        'application_no': admission.application_no,
        'redirect': '/dashboard/',
    })


@student_login_required
def my_application(request):
    reg_no = request.session.get('reg_no')
    admissions = StudentAdmission.objects.filter(reg_no=reg_no).order_by('-submitted_date', '-created_date')
    ctx = {'admissions': admissions}
    ctx.update(get_student_sidebar_context(reg_no, active='applications'))
    return render(request, 'admissions/my_application.html', ctx)


@student_login_required
def print_application(request, app_no):
    reg_no = request.session.get('reg_no')
    admission = get_printable_admission(reg_no, app_no)
    if not admission:
        messages.error(request, 'Submitted application not found.')
        return redirect('student_dashboard')
    return render(
        request,
        'admissions/print_full.html',
        get_application_print_view_context(admission, preview_mode=True),
    )


@student_login_required
def download_pdf_page(request):
    reg_no = request.session.get('reg_no')
    admission = get_printable_admission(reg_no)
    ctx = {'admission': admission}
    ctx.update(get_student_sidebar_context(reg_no, active='pdf'))
    return render(request, 'admissions/download_pdf.html', ctx)


@student_login_required
def download_pdf(request, app_no):
    reg_no = request.session.get('reg_no')
    admission = get_printable_admission(reg_no, app_no)
    if not admission:
        messages.error(request, 'Submitted application not found.')
        return redirect('student_dashboard')
    try:
        pdf_buffer = render_admission_pdf(admission, request)
    except Exception as exc:
        messages.error(request, f'PDF generation failed: {exc}')
        return redirect('download_pdf_page')

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{app_no}_application.pdf"'
    return response