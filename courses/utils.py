from .constants import PROGRAM_LEVEL_CHOICES
from .docx_import import infer_program_level
from .models import Program, ProgramCourse

_DIPLOMA_NAME_MARKERS = ('D. C. A', 'P. G. D. C. A', 'DIPLOMA')


def sync_programs_from_courses():
    """Create Program records from distinct course program_type values."""
    created = 0
    for name in (
        ProgramCourse.objects.exclude(program_type='')
        .values_list('program_type', flat=True)
        .distinct()
        .order_by('program_type')
    ):
        _, was_created = Program.objects.get_or_create(
            program_name=name,
            defaults={
                'program_level': infer_program_level(name),
                'is_active': True,
            },
        )
        if was_created:
            created += 1
    return created


def resolve_program_level(program_name: str, stored_level: str = '') -> str:
    """Return UG / PG / Diploma for a program name."""
    level = (stored_level or '').strip()
    if level in PROGRAM_LEVEL_CHOICES:
        return level
    inferred = infer_program_level(program_name)
    if inferred in PROGRAM_LEVEL_CHOICES:
        return inferred
    upper = (program_name or '').upper()
    if any(marker in upper for marker in _DIPLOMA_NAME_MARKERS):
        return 'Diploma'
    return ''


def get_program_level_for_name(program_name: str) -> str:
    program_name = (program_name or '').strip()
    if not program_name:
        return ''
    program = Program.objects.filter(program_name=program_name).first()
    if program:
        return resolve_program_level(program.program_name, program.program_level)
    return resolve_program_level(program_name)


def get_programs_by_level(active_only=True) -> dict[str, list[str]]:
    """Group active program names under UG / PG / Diploma for admission dropdowns."""
    grouped = {level: [] for level in PROGRAM_LEVEL_CHOICES}
    seen: set[str] = set()

    qs = Program.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    programs = list(qs.order_by('program_level', 'program_name'))

    if not programs:
        for name in (
            ProgramCourse.objects.exclude(program_type='')
            .values_list('program_type', flat=True)
            .distinct()
            .order_by('program_type')
        ):
            programs.append(Program(program_name=name, program_level=resolve_program_level(name)))

    for program in programs:
        name = (program.program_name or '').strip()
        if not name or name in seen:
            continue
        level = resolve_program_level(name, program.program_level)
        if level not in grouped:
            grouped[level] = []
        grouped[level].append(name)
        seen.add(name)

    for level in grouped:
        grouped[level].sort()
    return grouped


def get_program_names(active_only=True):
    """Program names for dropdowns; falls back to legacy course types if Programs empty."""
    qs = Program.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    names = list(qs.order_by('program_level', 'program_name').values_list('program_name', flat=True))
    if names:
        return names
    return list(
        ProgramCourse.objects.exclude(program_type='')
        .values_list('program_type', flat=True)
        .distinct()
        .order_by('program_type')
    )