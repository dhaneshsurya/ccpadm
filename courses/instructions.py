from .models import ProgramCourseInstruction


def get_program_course_instructions(program_name):
    """Return active instruction blocks for the selected program (admission form)."""
    name = (program_name or '').strip()
    if not name:
        return []

    rows = (
        ProgramCourseInstruction.objects.filter(
            program__program_name=name,
            program__is_active=True,
            is_active=True,
        )
        .select_related('program')
        .order_by('sort_order', 'id')
    )
    return [
        {
            'title': row.title.strip(),
            'message': row.message.strip(),
        }
        for row in rows
        if row.message.strip()
    ]