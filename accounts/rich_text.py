from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


def clean_rich_text(value, *, field_label='Content'):
    text = (value or '').strip()
    if not strip_tags(text).replace('\xa0', ' ').strip():
        raise ValidationError(f'{field_label} cannot be empty.')
    return text