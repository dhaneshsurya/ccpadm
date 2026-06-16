from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.utils import admin_login_required

from .constants import (
    COURSE_TYPE_1_CHOICES,
    COURSE_TYPE_2_CHOICES,
    PROGRAM_LEVEL_CHOICES,
    choices_with_current,
)
from .course_display import program_shows_department_in_course_name
from .docx_import import import_ug_courses_from_docx
from .models import Program, ProgramCourse
from .subject_groups import (
    course_is_group_course,
    get_subject_groups_queryset,
    group_label_for_course,
    is_bsc_program,
    save_course_subject_groups,
)
from .utils import get_program_names, sync_programs_from_courses

DEFAULT_UG_DOCX_PATH = r'C:\Users\LEGION\Downloads\UG First Semester  Course Information Dec 2025.docx'


def _filter_querystring(request):
    params = {}
    for key in ('search', 'program', 'type1', 'type2', 'level'):
        value = request.GET.get(key, '').strip() or request.POST.get(key, '').strip()
        if value and value != 'ALL':
            params[key] = value
        elif key in ('program', 'type1', 'type2', 'level') and value == 'ALL':
            params[key] = value
    return params


def _manage_courses_url(params=None, edit_pk=None):
    from django.urls import reverse
    from urllib.parse import urlencode

    query = dict(params or {})
    if edit_pk:
        query['edit'] = edit_pk
    base = reverse('manage_courses')
    if not query:
        return base
    return f'{base}?{urlencode(query)}'


def _manage_programs_url(params=None, edit_pk=None):
    from django.urls import reverse
    from urllib.parse import urlencode

    query = dict(params or {})
    if edit_pk:
        query['edit'] = edit_pk
    base = reverse('manage_programs')
    if not query:
        return base
    return f'{base}?{urlencode(query)}'


@admin_login_required
def manage_courses(request):
    courses = ProgramCourse.objects.prefetch_related('subject_groups')
    search = request.GET.get('search', '').strip()
    program_filter = request.GET.get('program', 'ALL')
    type1_filter = request.GET.get('type1', 'ALL')
    type2_filter = request.GET.get('type2', 'ALL')
    edit_pk = request.GET.get('edit', '').strip()

    if search:
        courses = courses.filter(
            Q(course_name__icontains=search)
            | Q(department__icontains=search)
            | Q(program_type__icontains=search)
        )
    if program_filter != 'ALL':
        courses = courses.filter(program_type=program_filter)
    if type1_filter != 'ALL':
        courses = courses.filter(course_type_1=type1_filter)
    if type2_filter != 'ALL':
        courses = courses.filter(course_type_2=type2_filter)

    program_types = get_program_names(active_only=False)
    type2_options = (
        ProgramCourse.objects.exclude(course_type_2='')
        .values_list('course_type_2', flat=True)
        .distinct()
        .order_by('course_type_2')
    )

    edit_course = None
    if edit_pk:
        edit_course = (
            ProgramCourse.objects.prefetch_related('subject_groups')
            .filter(pk=edit_pk)
            .first()
        )

    filter_params = {
        'search': search,
        'program': program_filter,
        'type1': type1_filter,
        'type2': type2_filter,
    }

    current_type1 = edit_course.course_type_1 if edit_course else ''
    current_type2 = edit_course.course_type_2 if edit_course else ''
    if edit_course:
        current_program = edit_course.program_type
    elif program_filter != 'ALL':
        current_program = program_filter
    else:
        current_program = ''

    show_bsc_groups = is_bsc_program(program_filter)
    show_group_field = is_bsc_program(current_program)
    available_subject_groups = (
        list(get_subject_groups_queryset(current_program))
        if show_group_field else []
    )
    selected_subject_group_ids = set()
    if edit_course:
        selected_subject_group_ids = set(
            edit_course.subject_groups.values_list('pk', flat=True),
        )

    program_department_flags = {}
    course_list = list(courses)
    for course in course_list:
        if course.program_type not in program_department_flags:
            program_department_flags[course.program_type] = (
                program_shows_department_in_course_name(course.program_type)
            )
        course.show_department_in_name = program_department_flags[course.program_type]
        if show_bsc_groups and is_bsc_program(course.program_type):
            course.subject_group_label = group_label_for_course(
                course.department,
                course.course_type_2,
                course.program_type,
                course=course,
            )
        else:
            course.subject_group_label = ''

    show_department_in_course_name = True
    if program_filter != 'ALL':
        show_department_in_course_name = program_shows_department_in_course_name(
            program_filter,
        )

    return render(request, 'courses/manage_courses.html', {
        'courses': course_list,
        'show_bsc_groups': show_bsc_groups,
        'program_types': program_types,
        'program_form_choices': choices_with_current(tuple(program_types), current_program),
        'type2_options': type2_options,
        'type1_choices': choices_with_current(COURSE_TYPE_1_CHOICES, current_type1),
        'type2_choices': choices_with_current(COURSE_TYPE_2_CHOICES, current_type2),
        'selected_program': current_program,
        'search': search,
        'program_filter': program_filter,
        'type1_filter': type1_filter,
        'type2_filter': type2_filter,
        'edit_course': edit_course,
        'filter_params': filter_params,
        'show_group_field': show_group_field,
        'available_subject_groups': available_subject_groups,
        'selected_subject_group_ids': selected_subject_group_ids,
        'show_department_in_course_name': show_department_in_course_name,
    })


@admin_login_required
def manage_programs(request):
    if not Program.objects.exists():
        created = sync_programs_from_courses()
        if created:
            messages.info(
                request,
                f'Imported {created} program(s) from existing courses. Set UG/PG/Diploma for each.',
            )

    programs = Program.objects.all()
    search = request.GET.get('search', '').strip()
    level_filter = request.GET.get('level', 'ALL')
    edit_pk = request.GET.get('edit', '').strip()

    if search:
        programs = programs.filter(
            Q(program_name__icontains=search)
            | Q(program_code__icontains=search)
        )
    if level_filter != 'ALL':
        programs = programs.filter(program_level=level_filter)

    edit_program = None
    if edit_pk:
        edit_program = Program.objects.filter(pk=edit_pk).first()

    current_level = edit_program.program_level if edit_program else ''

    return render(request, 'courses/manage_programs.html', {
        'programs': programs.order_by('program_level', 'program_name'),
        'search': search,
        'level_filter': level_filter,
        'edit_program': edit_program,
        'level_choices': PROGRAM_LEVEL_CHOICES,
        'selected_level': current_level,
        'filter_params': {'search': search, 'level': level_filter},
    })


@admin_login_required
@require_http_methods(['POST'])
def add_course(request):
    course = ProgramCourse.objects.create(
        program_type=request.POST.get('program_type', '').strip(),
        department=request.POST.get('department', '').strip(),
        course_name=request.POST.get('course_name', '').strip(),
        course_type_1=request.POST.get('course_type_1', '').strip(),
        course_type_2=request.POST.get('course_type_2', '').strip(),
        is_compulsory=request.POST.get('is_compulsory') == 'on',
        sort_order=(ProgramCourse.objects.count() + 1),
        created_by=request.session.get('admin_user', 'Admin'),
        created_date=timezone.now(),
    )
    if request.POST.get('has_subject_group_field') == '1':
        save_course_subject_groups(
            course,
            request.POST.getlist('subject_groups'),
        )
    messages.success(request, 'Course added successfully.')
    return redirect(_manage_courses_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def edit_course(request, pk):
    course = get_object_or_404(ProgramCourse, pk=pk)
    course.program_type = request.POST.get('program_type', '').strip()
    course.department = request.POST.get('department', '').strip()
    course.course_name = request.POST.get('course_name', '').strip()
    course.course_type_1 = request.POST.get('course_type_1', '').strip()
    course.course_type_2 = request.POST.get('course_type_2', '').strip()
    course.is_compulsory = request.POST.get('is_compulsory') == 'on'
    course.modified_by = request.session.get('admin_user', 'Admin')
    course.modified_date = timezone.now()
    course.save()
    if request.POST.get('has_subject_group_field') == '1':
        save_course_subject_groups(
            course,
            request.POST.getlist('subject_groups'),
        )
    messages.success(request, 'Course updated successfully.')
    return redirect(_manage_courses_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def add_program(request):
    program_name = request.POST.get('program_name', '').strip()
    program_level = request.POST.get('program_level', '').strip()
    program_code = request.POST.get('program_code', '').strip()

    if not program_name:
        messages.error(request, 'Program name is required.')
        return redirect(_manage_programs_url(_filter_querystring(request)))

    if program_level not in PROGRAM_LEVEL_CHOICES:
        messages.error(request, 'Please select a valid program type (UG, PG, or Diploma).')
        return redirect(_manage_programs_url(_filter_querystring(request)))

    if Program.objects.filter(program_name__iexact=program_name).exists():
        messages.error(request, f'Program "{program_name}" already exists.')
        return redirect(_manage_programs_url(_filter_querystring(request)))

    Program.objects.create(
        program_name=program_name,
        program_level=program_level,
        program_code=program_code,
        is_active=request.POST.get('is_active') == 'on',
    )
    messages.success(request, 'Program added successfully.')
    return redirect(_manage_programs_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def edit_program(request, pk):
    program = get_object_or_404(Program, pk=pk)
    program_name = request.POST.get('program_name', '').strip()
    program_level = request.POST.get('program_level', '').strip()
    program_code = request.POST.get('program_code', '').strip()

    if not program_name:
        messages.error(request, 'Program name is required.')
        return redirect(_manage_programs_url(_filter_querystring(request), edit_pk=pk))

    if program_level not in PROGRAM_LEVEL_CHOICES:
        messages.error(request, 'Please select a valid program type (UG, PG, or Diploma).')
        return redirect(_manage_programs_url(_filter_querystring(request), edit_pk=pk))

    if (
        Program.objects.filter(program_name__iexact=program_name)
        .exclude(pk=pk)
        .exists()
    ):
        messages.error(request, f'Program "{program_name}" already exists.')
        return redirect(_manage_programs_url(_filter_querystring(request), edit_pk=pk))

    old_name = program.program_name
    program.program_name = program_name
    program.program_level = program_level
    program.program_code = program_code
    program.is_active = request.POST.get('is_active') == 'on'
    program.save()

    if old_name != program_name:
        ProgramCourse.objects.filter(program_type=old_name).update(program_type=program_name)

    messages.success(request, 'Program updated successfully.')
    return redirect(_manage_programs_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def toggle_show_department(request):
    program_name = request.POST.get('program', '').strip()
    if not program_name or program_name == 'ALL':
        messages.error(request, 'Select a program to change department display.')
        return redirect(_manage_courses_url(_filter_querystring(request)))

    program = Program.objects.filter(program_name=program_name).first()
    if not program:
        messages.error(
            request,
            f'Program "{program_name}" was not found. Add it on Manage Programs first.',
        )
        return redirect(_manage_courses_url(_filter_querystring(request)))

    program.show_department_in_course_name = not program.show_department_in_course_name
    program.save(update_fields=['show_department_in_course_name'])
    state = 'shown' if program.show_department_in_course_name else 'hidden'
    messages.success(
        request,
        f'Department name is now {state} before course names for "{program_name}".',
    )
    return redirect(_manage_courses_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def toggle_compulsory(request, pk):
    course = get_object_or_404(ProgramCourse, pk=pk)
    course.is_compulsory = not course.is_compulsory
    course.modified_by = request.session.get('admin_user', 'Admin')
    course.modified_date = timezone.now()
    course.save()
    label = 'marked compulsory' if course.is_compulsory else 'unmarked compulsory'
    messages.success(request, f'"{course.course_name}" {label}.')
    return redirect(_manage_courses_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def delete_course(request, pk):
    ProgramCourse.objects.filter(pk=pk).delete()
    messages.success(request, 'Course deleted.')
    return redirect(_manage_courses_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def delete_program(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if ProgramCourse.objects.filter(program_type=program.program_name).exists():
        messages.error(
            request,
            f'Cannot delete "{program.program_name}" — courses are still linked. Remove or reassign courses first.',
        )
        return redirect(_manage_programs_url(_filter_querystring(request)))

    program.delete()
    messages.success(request, 'Program deleted.')
    return redirect(_manage_programs_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def sync_programs(request):
    created = sync_programs_from_courses()
    if created:
        messages.success(request, f'Synced {created} new program(s) from existing courses.')
    else:
        messages.info(request, 'All course programs are already in the program list.')
    return redirect(_manage_programs_url(_filter_querystring(request)))


@admin_login_required
@require_http_methods(['POST'])
def import_ug_docx(request):
    uploaded = request.FILES.get('docx_file')
    replace_existing = request.POST.get('replace_ug') == 'on'

    if uploaded:
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)
        try:
            stats = import_ug_courses_from_docx(
                tmp_path,
                created_by=request.session.get('admin_user', 'Admin'),
                replace_existing_ug=replace_existing,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        from pathlib import Path

        docx_path = Path(DEFAULT_UG_DOCX_PATH)
        if not docx_path.exists():
            messages.error(request, f'Word file not found: {docx_path}')
            return redirect(_manage_courses_url(_filter_querystring(request)))

        stats = import_ug_courses_from_docx(
            docx_path,
            created_by=request.session.get('admin_user', 'Admin'),
            replace_existing_ug=replace_existing,
        )

    messages.success(
        request,
        (
            f'Imported {stats["rows_parsed"]} course row(s): '
            f'{stats["courses_created"]} created, {stats["courses_updated"]} updated; '
            f'{stats["programs_created"]} program(s) created, {stats["programs_updated"]} updated. '
            f'Removed {stats.get("programs_removed", 0)} duplicate UG program(s) and '
            f'{stats.get("legacy_courses_removed", 0)} legacy course row(s).'
        ),
    )
    return redirect(_manage_courses_url(_filter_querystring(request)))