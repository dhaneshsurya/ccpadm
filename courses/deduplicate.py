"""Remove legacy duplicate UG program names and their course rows."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from accounts.models import Student
from admissions.models import StudentAdmission

from .models import Program, ProgramCourse

# Legacy SQL-import names -> canonical names from the UG Word document.
UG_LEGACY_PROGRAM_MAP = {
    'B. A. - First Semester': 'B.A.',
    'B.COM - First Semester': 'B.COM',
    'B.Sc. Bio - First Semester': 'B.Sc.',
    'B.Sc. mathematics - First Semester': 'B.Sc.',
    'BBA - First Semester': 'BBA',
    'BCA - First Semester': 'BCA',
}

# B.Sc. specializations collapsed into a single B.Sc. program.
BSC_VARIANT_PROGRAMS = (
    'B.Sc. (Computer Science)',
    'B.Sc. (Life Science)',
    'B.Sc. (Physical Science)',
    'B.Sc. (Forestry)',
    'B.Sc. (Zoology)',
    'B.Sc.(Mathematics)',
)

BSC_CANONICAL_PROGRAM = 'B.Sc.'


def _migrate_program_references(old_name: str, new_name: str) -> dict[str, int]:
    stats = {'students': 0, 'admissions': 0}
    stats['students'] = Student.objects.filter(program_type=old_name).update(program_type=new_name)
    stats['admissions'] = StudentAdmission.objects.filter(program_type=old_name).update(program_type=new_name)
    return stats


def _course_exists(program_type: str, course: ProgramCourse) -> bool:
    return ProgramCourse.objects.filter(
        program_type=program_type,
        department=course.department,
        course_name=course.course_name,
        course_type_1=course.course_type_1,
        course_type_2=course.course_type_2,
    ).exclude(pk=course.pk).exists()


def _collapse_bsc_variant_programs() -> dict[str, int]:
    """Merge B.Sc. specialization programs into the single B.Sc. program."""
    stats = {
        'programs_removed': 0,
        'courses_merged': 0,
        'courses_removed': 0,
        'students_migrated': 0,
        'admissions_migrated': 0,
    }

    Program.objects.get_or_create(
        program_name=BSC_CANONICAL_PROGRAM,
        defaults={'program_level': 'UG', 'is_active': True},
    )

    for variant_name in BSC_VARIANT_PROGRAMS:
        migrate_stats = _migrate_program_references(variant_name, BSC_CANONICAL_PROGRAM)
        stats['students_migrated'] += migrate_stats['students']
        stats['admissions_migrated'] += migrate_stats['admissions']

        for course in ProgramCourse.objects.filter(program_type=variant_name):
            if _course_exists(BSC_CANONICAL_PROGRAM, course):
                course.delete()
                stats['courses_removed'] += 1
            else:
                course.program_type = BSC_CANONICAL_PROGRAM
                course.save(update_fields=['program_type'])
                stats['courses_merged'] += 1

        deleted, _ = Program.objects.filter(program_name=variant_name).delete()
        stats['programs_removed'] += deleted

    stats['courses_removed'] += _remove_duplicate_courses_in_program(BSC_CANONICAL_PROGRAM)
    return stats


def _remove_duplicate_courses_in_program(program_type: str) -> int:
    """Drop rows that repeat the same course identity; keep the row with a department."""
    removed = 0
    duplicate_groups = (
        ProgramCourse.objects.filter(program_type=program_type)
        .values('course_name', 'course_type_1', 'course_type_2')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )
    for group in duplicate_groups:
        rows = list(
            ProgramCourse.objects.filter(
                program_type=program_type,
                course_name=group['course_name'],
                course_type_1=group['course_type_1'],
                course_type_2=group['course_type_2'],
            ).order_by('-department', 'id')
        )
        for duplicate in rows[1:]:
            duplicate.delete()
            removed += 1
    return removed


@transaction.atomic
def deduplicate_ug_programs_and_courses() -> dict[str, int]:
    """Merge legacy UG program labels and delete their duplicate course lists."""
    stats = {
        'programs_removed': 0,
        'courses_removed': 0,
        'courses_deduped': 0,
        'students_migrated': 0,
        'admissions_migrated': 0,
    }

    canonical_names = set(UG_LEGACY_PROGRAM_MAP.values())

    for old_name, new_name in UG_LEGACY_PROGRAM_MAP.items():
        if not Program.objects.filter(program_name=new_name).exists():
            Program.objects.filter(program_name=old_name).update(
                program_name=new_name,
                program_level='UG',
            )
            continue

        migrate_stats = _migrate_program_references(old_name, new_name)
        stats['students_migrated'] += migrate_stats['students']
        stats['admissions_migrated'] += migrate_stats['admissions']

        deleted, _ = ProgramCourse.objects.filter(program_type=old_name).delete()
        stats['courses_removed'] += deleted

        deleted, _ = Program.objects.filter(program_name=old_name).delete()
        stats['programs_removed'] += deleted

    for program_name in canonical_names:
        stats['courses_deduped'] += _remove_duplicate_courses_in_program(program_name)

    bsc_stats = _collapse_bsc_variant_programs()
    stats['programs_removed'] += bsc_stats['programs_removed']
    stats['courses_removed'] += bsc_stats['courses_removed']
    stats['courses_deduped'] += bsc_stats['courses_removed']
    stats['students_migrated'] += bsc_stats['students_migrated']
    stats['admissions_migrated'] += bsc_stats['admissions_migrated']
    stats['bsc_courses_merged'] = bsc_stats['courses_merged']

    return stats