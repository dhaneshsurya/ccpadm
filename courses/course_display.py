from .models import Program
from .subject_groups import normalize_department


def program_shows_department_in_course_name(program_name: str) -> bool:
    """Whether students and course lists prefix department before the paper name."""
    name = (program_name or '').strip()
    if not name:
        return True
    row = (
        Program.objects.filter(program_name=name)
        .only('show_department_in_course_name')
        .first()
    )
    if row is None:
        return True
    return row.show_department_in_course_name


def format_course_display_name(course_name, department, *, program_name: str) -> str:
    paper = (course_name or '').strip()
    dept = normalize_department(department)
    if dept and program_shows_department_in_course_name(program_name):
        return f'{dept} — {paper}'
    return paper