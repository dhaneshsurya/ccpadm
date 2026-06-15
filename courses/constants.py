COURSE_TYPE_1_CHOICES = ('Theory', 'Practical')

COURSE_TYPE_2_CHOICES = ('DSC', 'GE', 'AEC', 'SEC', 'DSE', 'VAC')

PROGRAM_LEVEL_CHOICES = ('UG', 'PG', 'Diploma')

PROGRAM_LEVEL_DISPLAY = {
    'UG': 'First Under Graduate',
    'PG': 'Post Graduate',
    'Diploma': 'Diploma',
}


def choices_with_current(base_choices, current=''):
    """Include legacy DB value in dropdown when editing old records."""
    current = (current or '').strip()
    if current and current not in base_choices:
        return (current,) + base_choices
    return base_choices