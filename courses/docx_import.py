"""Parse UG course information from the college Word document."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone

from .constants import COURSE_TYPE_1_CHOICES, COURSE_TYPE_2_CHOICES
from .deduplicate import deduplicate_ug_programs_and_courses
from .models import Program, ProgramCourse

DOCX_HEADER = [
    'Department', 'Sem.', 'Program', 'ProgramCode', 'PaperCode', 'CourseCode',
    'Course Name', 'PaperNo.', 'CourseType', 'L', 'T', 'P', 'TotalCredit',
    'CiaMarks', 'EseMarks', 'MaxMarks', 'MinMarks', 'CourseType', 'Intake',
]

PROGRAM_NAME_ALIASES = {
    'B.Sc. PhysicalScience)': 'B.Sc.',
    'B.Sc. (Physical Science)': 'B.Sc.',
    'B.Sc. (Life Science)': 'B.Sc.',
    'B.Sc. (Computer Science)': 'B.Sc.',
    'B.Sc. (Forestry)': 'B.Sc.',
    'B.Sc. (Zoology)': 'B.Sc.',
    'B.Sc.(Mathematics)': 'B.Sc.',
}

UG_PROGRAM_PREFIXES = (
    'B.', 'B.A', 'B.Sc', 'B.COM', 'BBA', 'BCA', 'B.Com', 'B.Com.',
)


@dataclass(frozen=True)
class DocxCourseRow:
    program: str
    department: str
    course_name: str
    course_type_1: str
    course_type_2: str
    program_code: str = ''

    @property
    def display_course_label(self) -> str:
        if self.department:
            return f'{self.department} — {self.course_name}'
        return self.course_name


def normalize_program_name(name: str) -> str:
    name = (name or '').strip()
    return PROGRAM_NAME_ALIASES.get(name, name)


def infer_program_level(program_name: str) -> str:
    upper = program_name.upper()
    if upper.startswith('M.') or upper.startswith('M '):
        return 'PG'
    if 'DIPLOMA' in upper:
        return 'Diploma'
    if any(upper.startswith(prefix.upper()) for prefix in UG_PROGRAM_PREFIXES):
        return 'UG'
    return ''


def parse_ug_courses_docx(path: str | Path) -> list[DocxCourseRow]:
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        xml = archive.read('word/document.xml')

    root = ET.fromstring(xml)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    rows: list[DocxCourseRow] = []

    for table in root.findall('.//w:tbl', ns):
        has_header = False
        for tr in table.findall('w:tr', ns):
            cells = []
            for tc in tr.findall('w:tc', ns):
                texts = [node.text or '' for node in tc.findall('.//w:t', ns)]
                cells.append(''.join(texts).strip())
            if not any(cells):
                continue
            if cells[: len(DOCX_HEADER)] == DOCX_HEADER:
                has_header = True
                continue
            if len(cells) == 1:
                continue
            if len(cells) < 18:
                continue

            program = normalize_program_name(cells[2])
            department = cells[0].strip()
            course_name = cells[6].strip()
            course_type_1 = cells[8].strip()
            course_type_2 = cells[17].strip()
            program_code = cells[3].strip() if len(cells) > 3 else ''

            if not program or not course_name:
                continue
            if course_type_1 not in COURSE_TYPE_1_CHOICES:
                continue
            if course_type_2 not in COURSE_TYPE_2_CHOICES:
                continue

            rows.append(
                DocxCourseRow(
                    program=program,
                    department=department,
                    course_name=course_name,
                    course_type_1=course_type_1,
                    course_type_2=course_type_2,
                    program_code=program_code,
                )
            )

    return rows


def import_ug_courses_from_docx(
    path: str | Path,
    *,
    created_by: str = 'Admin',
    replace_existing_ug: bool = False,
) -> dict[str, int]:
    """Import programs and courses from the UG first-semester Word document."""
    rows = parse_ug_courses_docx(path)
    if not rows:
        return {'courses_created': 0, 'courses_updated': 0, 'programs_created': 0, 'programs_updated': 0}

    if replace_existing_ug:
        ug_program_names = {row.program for row in rows}
        ProgramCourse.objects.filter(program_type__in=ug_program_names).delete()

    program_codes: dict[str, str] = {}
    for row in rows:
        if row.program_code:
            program_codes.setdefault(row.program, row.program_code)

    programs_created = 0
    programs_updated = 0
    for program_name in sorted({row.program for row in rows}):
        defaults = {
            'program_level': infer_program_level(program_name) or 'UG',
            'program_code': program_codes.get(program_name, ''),
            'is_active': True,
        }
        program, created = Program.objects.get_or_create(
            program_name=program_name,
            defaults=defaults,
        )
        if created:
            programs_created += 1
        else:
            changed = False
            if not program.program_level and defaults['program_level']:
                program.program_level = defaults['program_level']
                changed = True
            if defaults['program_code'] and program.program_code != defaults['program_code']:
                program.program_code = defaults['program_code']
                changed = True
            if not program.is_active:
                program.is_active = True
                changed = True
            if changed:
                program.save()
                programs_updated += 1

    courses_created = 0
    courses_updated = 0
    sort_order = ProgramCourse.objects.count()

    for index, row in enumerate(rows, start=1):
        lookup = {
            'program_type': row.program,
            'department': row.department,
            'course_name': row.course_name,
            'course_type_1': row.course_type_1,
            'course_type_2': row.course_type_2,
        }
        course = ProgramCourse.objects.filter(**lookup).first()
        if course:
            course.modified_by = created_by
            course.modified_date = timezone.now()
            course.save(update_fields=['modified_by', 'modified_date'])
            courses_updated += 1
            continue

        ProgramCourse.objects.create(
            program_type=row.program,
            department=row.department,
            course_name=row.course_name,
            course_type_1=row.course_type_1,
            course_type_2=row.course_type_2,
            sort_order=sort_order + index,
            created_by=created_by,
            created_date=timezone.now(),
        )
        courses_created += 1

    dedupe_stats = deduplicate_ug_programs_and_courses()

    return {
        'courses_created': courses_created,
        'courses_updated': courses_updated,
        'programs_created': programs_created,
        'programs_updated': programs_updated,
        'rows_parsed': len(rows),
        'programs_removed': dedupe_stats['programs_removed'],
        'legacy_courses_removed': dedupe_stats['courses_removed'],
        'courses_deduped': dedupe_stats['courses_deduped'],
        'students_migrated': dedupe_stats['students_migrated'],
        'admissions_migrated': dedupe_stats['admissions_migrated'],
    }