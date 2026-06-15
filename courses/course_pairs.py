from .models import ProgramCourse


def link_theory_practical_pair(program_type, theory_name, practical_name):
    """Link theory → practical/lab auto-selection for a program."""
    theory = ProgramCourse.objects.filter(
        program_type=program_type,
        course_name=theory_name,
    ).first()
    practical = ProgramCourse.objects.filter(
        program_type=program_type,
        course_name=practical_name,
    ).first()
    if not theory or not practical:
        return False
    if theory.auto_select_course_id != practical.pk:
        theory.auto_select_course = practical
        theory.save(update_fields=['auto_select_course'])
    return True