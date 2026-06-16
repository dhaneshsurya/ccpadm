from .models import AdmissionSubmitInstruction


def get_admission_submit_instruction():
    """Return the active submit-popup instruction for the admission preview page."""
    row = (
        AdmissionSubmitInstruction.objects.filter(is_active=True)
        .order_by('sort_order', 'id')
        .first()
    )
    if not row:
        return None
    return {
        'heading': row.heading.strip(),
        'notice': row.notice.strip(),
    }