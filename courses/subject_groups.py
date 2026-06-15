"""B.Sc. DSC subject group configuration for admission course selection."""

from __future__ import annotations

import re

BSC_PROGRAM = 'B.Sc.'
_BSC_PROGRAM_RE = re.compile(r'^b\.sc', re.IGNORECASE)

BSC_SUBJECT_GROUP_SECTIONS = (
    {
        'heading': 'B.Sc. Bio Group',
        'groups': (
            {
                'key': 'bio_a',
                'label': 'Group A',
                'departments': ('Chemistry', 'Botany', 'Zoology'),
            },
            {
                'key': 'bio_b',
                'label': 'Group B',
                'departments': ('Chemistry', 'Forestry', 'Zoology'),
            },
        ),
    },
    {
        'heading': 'B.Sc. Maths Group',
        'groups': (
            {
                'key': 'maths_a',
                'label': 'Group A',
                'departments': ('Chemistry', 'Mathematics', 'Physics'),
            },
            {
                'key': 'maths_b',
                'label': 'Group B',
                'departments': ('Computer Science', 'Mathematics', 'Physics'),
            },
        ),
    },
)


def is_bsc_program(program_type: str) -> bool:
    """True for canonical B.Sc. and legacy/import variants (e.g. B.Sc. First Semester)."""
    name = (program_type or '').strip()
    if not name:
        return False
    if name == BSC_PROGRAM:
        return True
    if _BSC_PROGRAM_RE.match(name):
        return True
    try:
        from .deduplicate import BSC_VARIANT_PROGRAMS

        if name in BSC_VARIANT_PROGRAMS:
            return True
    except ImportError:
        pass
    return False


def resolve_bsc_courses_program_type(program_type: str = '') -> str:
    """Return the ProgramCourse.program_type row set used for B.Sc. courses."""
    from .models import ProgramCourse

    requested = (program_type or '').strip()
    if requested and ProgramCourse.objects.filter(program_type=requested).exists():
        return requested
    match = (
        ProgramCourse.objects.filter(program_type__iregex=r'^b\.sc')
        .values_list('program_type', flat=True)
        .distinct()
        .order_by('program_type')
        .first()
    )
    return match or BSC_PROGRAM


def normalize_program_type_for_display(program_type: str, program_types: list[str] | tuple[str, ...]) -> str:
    """Map stored B.Sc. aliases to the name shown in program dropdowns."""
    name = (program_type or '').strip()
    if not name:
        return ''
    if name in program_types:
        return name
    if is_bsc_program(name):
        for candidate in program_types:
            if is_bsc_program(candidate):
                return candidate
    return name


def _default_bsc_subject_group_sections() -> list[dict]:
    return [
        {
            'heading': section['heading'],
            'groups': [
                {
                    'key': group['key'],
                    'label': group['label'],
                    'departments': list(group['departments']),
                    'department_label': ', '.join(group['departments']),
                    'full_name': f"{section['heading']} — {group['label']}",
                }
                for group in section['groups']
            ],
        }
        for section in BSC_SUBJECT_GROUP_SECTIONS
    ]


def _group_dict_from_model(group) -> dict:
    return {
        'key': group.group_key,
        'label': group.group_label,
        'departments': group.department_list,
        'department_label': group.department_label,
        'full_name': group.full_name,
    }


def _sections_from_db_groups(groups) -> list[dict]:
    sections: dict[str, list[dict]] = {}
    order: list[str] = []
    for group in groups:
        heading = group.section_heading
        if heading not in sections:
            sections[heading] = []
            order.append(heading)
        sections[heading].append(_group_dict_from_model(group))
    return [{'heading': heading, 'groups': sections[heading]} for heading in order]


def _resolve_program_for_groups(program_type: str):
    from .models import Program

    program_type = (program_type or '').strip()
    if not program_type:
        return None
    program = Program.objects.filter(program_name=program_type).first()
    if program:
        return program
    if is_bsc_program(program_type):
        course_program = resolve_bsc_courses_program_type(program_type)
        return Program.objects.filter(program_name=course_program).first()
    return None


def _db_groups_queryset(program_type: str = ''):
    from .models import ProgramSubjectGroup

    program = _resolve_program_for_groups(program_type)
    if not program:
        return ProgramSubjectGroup.objects.none()
    return ProgramSubjectGroup.objects.filter(program=program).order_by(
        'sort_order', 'section_heading', 'group_key',
    )


def seed_default_bsc_groups_for_program(program) -> int:
    """Create default B.Sc. groups on a program if none exist. Returns rows created."""
    from .models import ProgramSubjectGroup

    if not is_bsc_program(program.program_name):
        return 0
    if ProgramSubjectGroup.objects.filter(program=program).exists():
        return 0

    created = 0
    sort_order = 0
    for section in BSC_SUBJECT_GROUP_SECTIONS:
        for group in section['groups']:
            ProgramSubjectGroup.objects.create(
                program=program,
                section_heading=section['heading'],
                group_key=group['key'],
                group_label=group['label'],
                departments=', '.join(group['departments']),
                sort_order=sort_order,
            )
            sort_order += 1
            created += 1
    return created


def get_bsc_subject_group_sections(program_type: str = '') -> list[dict]:
    """Return group config for the courses API / admission form."""
    db_groups = _db_groups_queryset(program_type)
    if db_groups.exists():
        return _sections_from_db_groups(db_groups)
    return _default_bsc_subject_group_sections()


def get_all_bsc_group_departments(program_type: str = '') -> set[str]:
    sections = get_bsc_subject_group_sections(program_type)
    departments: set[str] = set()
    for section in sections:
        for group in section['groups']:
            departments.update(group['departments'])
    return departments


def normalize_department(department: str) -> str:
    return (department or '').strip()


def get_bsc_group_by_key(group_key: str, program_type: str = '') -> dict | None:
    group_key = (group_key or '').strip()
    if not group_key:
        return None

    db_groups = _db_groups_queryset(program_type)
    if db_groups.exists():
        match = db_groups.filter(group_key=group_key).first()
        if match:
            return {
                'key': match.group_key,
                'label': match.group_label,
                'heading': match.section_heading,
                'departments': set(match.department_list),
            }

    for section in BSC_SUBJECT_GROUP_SECTIONS:
        for group in section['groups']:
            if group['key'] == group_key:
                return {
                    'key': group['key'],
                    'label': group['label'],
                    'heading': section['heading'],
                    'departments': set(group['departments']),
                }
    return None


def get_bsc_group_labels(program_type: str = '') -> dict[str, str]:
    labels = {}
    for section in get_bsc_subject_group_sections(program_type):
        for group in section['groups']:
            labels[group['key']] = group['full_name']
    return labels


def department_in_group(department: str, group_key: str, program_type: str = '') -> bool:
    group = get_bsc_group_by_key(group_key, program_type)
    if not group:
        return False
    return normalize_department(department) in group['departments']


def course_matches_bsc_group(
    department: str,
    course_type_2: str,
    group_key: str,
    program_type: str = '',
) -> bool:
    group = get_bsc_group_by_key(group_key, program_type)
    if not group:
        return False
    return (
        (department or '').strip() in group['departments']
        and (course_type_2 or '').strip().upper() == 'DSC'
    )


def get_subject_groups_queryset(program_type: str = ''):
    """Return ProgramSubjectGroup rows for a program name."""
    return _db_groups_queryset(program_type)


def get_assigned_group_keys(course) -> list[str]:
    if not course or not getattr(course, 'pk', None):
        return []
    if hasattr(course, '_prefetched_objects_cache') and 'subject_groups' in course._prefetched_objects_cache:
        groups = course.subject_groups.all()
    else:
        groups = course.subject_groups.all()
    return [g.group_key for g in groups]


def get_assigned_group_labels(course) -> list[str]:
    if not course or not getattr(course, 'pk', None):
        return []
    return [g.full_name for g in course.subject_groups.all()]


def get_bsc_group_for_course(
    department: str,
    course_type_2: str,
    program_type: str = '',
    course=None,
) -> list[str]:
    """Return group keys for a course (explicit assignment, else DSC department match)."""
    assigned = get_assigned_group_keys(course) if course else []
    if assigned:
        return assigned
    if (course_type_2 or '').strip().upper() != 'DSC':
        return []
    department = (department or '').strip()
    keys = []
    for section in get_bsc_subject_group_sections(program_type):
        for group in section['groups']:
            if department in group['departments']:
                keys.append(group['key'])
    return keys


def group_label_for_course(
    department: str,
    course_type_2: str,
    program_type: str = '',
    course=None,
) -> str:
    labels = get_assigned_group_labels(course) if course else []
    if labels:
        return ', '.join(labels)
    keys = get_bsc_group_for_course(department, course_type_2, program_type)
    if not keys:
        return ''
    label_map = get_bsc_group_labels(program_type)
    return ', '.join(label_map[key] for key in keys)


def course_is_group_dsc(course, program_type: str = '') -> bool:
    """DSC course whose compulsory status is driven by B.Sc. group selection."""
    program_type = (program_type or getattr(course, 'program_type', '') or '').strip()
    if not is_bsc_program(program_type):
        return False
    if (getattr(course, 'course_type_2', '') or '').strip().upper() != 'DSC':
        return False
    if get_assigned_group_keys(course):
        return True
    department = normalize_department(getattr(course, 'department', ''))
    return department in get_all_bsc_group_departments(program_type)


def course_is_group_course(course, program_type: str = '') -> bool:
    """True when the course is shown/hidden based on the student's chosen B.Sc. group."""
    program_type = (program_type or getattr(course, 'program_type', '') or '').strip()
    if not is_bsc_program(program_type):
        return False
    if get_assigned_group_keys(course):
        return True
    return course_is_group_dsc(course, program_type)


def course_is_program_compulsory(course, program_type: str = '') -> bool:
    """True when is_compulsory from DB should auto-lock the course on the admission form."""
    if not getattr(course, 'is_compulsory', False):
        return False
    program_type = (program_type or getattr(course, 'program_type', '') or '').strip()
    if is_bsc_program(program_type) and course_is_group_dsc(course, program_type):
        return False
    return True


def save_course_subject_groups(course, group_ids) -> None:
    from .models import ProgramSubjectGroup

    valid_groups = get_subject_groups_queryset(course.program_type).filter(
        pk__in=group_ids or [],
    )
    course.subject_groups.set(valid_groups)