import base64
import json
import os
import re
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .models import StudentAdmission
from .services import pack_selected_subjects_json


def generate_application_number():
    date_part = timezone.now().strftime('%d%m%y')
    prefix = f'CCP{date_part}'
    last = (
        StudentAdmission.objects.filter(application_no__startswith=prefix)
        .order_by('-application_no')
        .values_list('application_no', flat=True)
        .first()
    )
    if last and len(last) >= 13:
        try:
            seq = int(last[-4:]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'


def save_base64_image(base64_string, app_no, image_type='photo'):
    if not base64_string:
        return None
    clean = base64_string
    extension = '.jpg'
    if ',' in base64_string:
        header, clean = base64_string.split(',', 1)
        if 'png' in header.lower():
            extension = '.png'
        elif 'gif' in header.lower():
            extension = '.gif'
    try:
        image_bytes = base64.b64decode(clean)
    except Exception:
        return None
    from pathlib import Path
    upload_dir = Path(settings.MEDIA_ROOT) / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f'{app_no}_{image_type}{extension}'
    filepath = upload_dir / filename
    with open(filepath, 'wb') as f:
        f.write(image_bytes)
    return str(filepath.relative_to(Path(settings.MEDIA_ROOT)))


def _edu_field(item, *keys, default=''):
    for key in keys:
        if key in item and item[key] not in (None, ''):
            return item[key]
    return default


def _education_has_meaningful_data(education_list):
    """True when at least one education row has user-entered values."""
    for item in education_list or []:
        if not isinstance(item, dict):
            continue
        for key in (
            'Board', 'board', 'Stream', 'stream', 'Year', 'year',
            'TotalMarks', 'totalMarks', 'total_marks', 'Obtained', 'obtained',
            'obtainedMarks', 'Percentage', 'percentage',
        ):
            if str(_edu_field(item, key)).strip():
                return True
    return False


def _load_education_json(admission):
    if not admission or not admission.education_json:
        return []
    try:
        stored = json.loads(admission.education_json)
        if isinstance(stored, list):
            return stored
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _education_row_key(item):
    cls = str(_edu_field(item, 'ClassName', 'className', 'class', 'Class')).lower()
    if any(x in cls for x in ('12', 'xii', 'inter', 'hsc', '+2', 'senior', 'higher')):
        return '12'
    if any(x in cls for x in ('grad', 'ug', 'bachelor', 'degree', 'b.')):
        return 'grad'
    return '10'


def _merge_education_lists(incoming, stored):
    if not stored:
        return incoming
    if not _education_has_meaningful_data(incoming):
        return stored
    merged = {_education_row_key(item): dict(item) for item in stored if isinstance(item, dict)}
    for item in incoming:
        if not isinstance(item, dict):
            continue
        key = _education_row_key(item)
        if _education_has_meaningful_data([item]):
            merged[key] = {**merged.get(key, {}), **item}
        elif key not in merged:
            merged[key] = dict(item)
    return list(merged.values())


def _resolve_application_no(data, reg_no):
    app_no = (data.get('application_no') or '').strip()
    if app_no:
        return app_no
    existing = (
        StudentAdmission.objects.filter(
            reg_no=reg_no,
            status__in=('Draft', 'Submitted', 'Pending'),
        )
        .order_by('-updated_date', '-created_date')
        .first()
    )
    if existing and existing.application_no:
        return existing.application_no
    return generate_application_number()


def parse_education(education_list):
    class10, class12, grad = {}, {}, {}
    for item in education_list or []:
        cls = str(_edu_field(item, 'ClassName', 'className', 'class', 'Class')).lower()
        target = None
        if any(x in cls for x in ('12', 'xii', 'inter', 'hsc', '+2', 'senior', 'higher')):
            target = class12
        elif any(x in cls for x in ('10', 'ssc', 'matric', 'secondary', 'high')) or cls == 'x':
            target = class10
        elif any(x in cls for x in ('grad', 'ug', 'bachelor', 'degree', 'b.')):
            target = grad
        if target is None:
            continue
        target.update({
            'class': _edu_field(item, 'ClassName', 'className', 'class', 'Class'),
            'board': _edu_field(item, 'Board', 'board'),
            'stream': _edu_field(item, 'Stream', 'stream'),
            'duration': _edu_field(item, 'Duration', 'duration'),
            'year': _edu_field(item, 'Year', 'year'),
            'total_marks': _edu_field(item, 'TotalMarks', 'totalMarks', 'total_marks'),
            'obtained': _edu_field(item, 'Obtained', 'obtainedMarks', 'obtained', 'obtained_marks'),
            'percentage': _edu_field(item, 'Percentage', 'percentage'),
            'grade': _edu_field(item, 'Grade', 'grade'),
        })
    return class10, class12, grad


def _safe_int(val):
    if val is None or val == '':
        return None
    try:
        return int(re.sub(r'\D', '', str(val)) or 0) or None
    except (ValueError, TypeError):
        return None


def save_admission_from_form(data, reg_no, status='Submitted'):
    app_no = _resolve_application_no(data, reg_no)
    existing = StudentAdmission.objects.filter(application_no=app_no).first()

    education = data.get('education', [])
    if isinstance(education, str):
        try:
            education = json.loads(education)
        except json.JSONDecodeError:
            education = []
    if not isinstance(education, list):
        education = []

    stored = _load_education_json(existing) if existing else []
    if stored and _education_has_meaningful_data(education):
        education = _merge_education_lists(education, stored)
    elif stored and not _education_has_meaningful_data(education):
        education = stored

    class10, class12, grad = parse_education(education)

    dob = data.get('dob')
    dob_val = None
    if dob:
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dob_val = datetime.strptime(dob, fmt).date()
                break
            except ValueError:
                continue

    defaults = {
        'reg_no': reg_no,
        'program_type': data.get('program_type', ''),
        'course_name': data.get('course_name', ''),
        'subject': data.get('subject', ''),
        'full_name': data.get('full_name', ''),
        'father_name': data.get('father_name', ''),
        'mother_name': data.get('mother_name', ''),
        'gender': data.get('gender', ''),
        'category': data.get('category', ''),
        'nationality': data.get('nationality', ''),
        'religion': data.get('religion', ''),
        'marital_status': data.get('marital_status', ''),
        'blood_group': data.get('blood_group', ''),
        'dob': dob_val,
        'mobile': data.get('mobile', ''),
        'email': data.get('email', ''),
        'aadhaar': data.get('aadhaar', ''),
        'apaar_id': data.get('apaar', '') or data.get('apaar_id', ''),
        'has_disability': data.get('has_disability') in (1, '1', True, 'yes', 'Yes'),
        'disability_details': data.get('disability_details', ''),
        'disability_percentage': data.get('disability_percentage', ''),
        'disability_type': data.get('disability_type', ''),
        'is_minority': data.get('minority') in (1, '1', True, 'yes', 'Yes'),
        'medium': data.get('medium', ''),
        'perm_state': data.get('perm_state', ''),
        'perm_district': data.get('perm_district', ''),
        'perm_city': data.get('perm_city', ''),
        'perm_village': data.get('perm_village', ''),
        'perm_pin_code': data.get('perm_pin_code', ''),
        'corr_state': data.get('corr_state', ''),
        'corr_district': data.get('corr_district', ''),
        'corr_city': data.get('corr_city', ''),
        'corr_village': data.get('corr_village', ''),
        'corr_pin_code': data.get('corr_pin_code', ''),
        'class10': class10.get('class', ''),
        'board10': class10.get('board', ''),
        'duration10': _safe_int(class10.get('duration')),
        'year10': _safe_int(class10.get('year')),
        'total_marks10': str(class10.get('total_marks', '')),
        'obtained10': str(class10.get('obtained', '')),
        'percentage10': str(class10.get('percentage', '')),
        'grade10': class10.get('grade', ''),
        'class12': class12.get('class', '') or (
            '12th' if any(str(class12.get(k, '')).strip() for k in ('board', 'stream', 'year', 'total_marks', 'obtained'))
            else ''
        ),
        'board12': class12.get('board', ''),
        'duration12': _safe_int(class12.get('duration')),
        'year12': _safe_int(class12.get('year')),
        'total_marks12': str(class12.get('total_marks', '')),
        'obtained12': str(class12.get('obtained', '')),
        'percentage12': str(class12.get('percentage', '')),
        'grade12': class12.get('grade', ''),
        'class_grad': grad.get('class', ''),
        'board_grad': grad.get('board', ''),
        'duration_grad': _safe_int(grad.get('duration')),
        'year_grad': _safe_int(grad.get('year')),
        'total_marks_grad': str(grad.get('total_marks', '')),
        'obtained_grad': str(grad.get('obtained', '')),
        'percentage_grad': str(grad.get('percentage', '')),
        'grade_grad': grad.get('grade', ''),
        'stream12': class12.get('stream', ''),
        'stream_grad': grad.get('stream', ''),
        'education_json': json.dumps(education) if education else '',
        'active_step': _safe_int(data.get('active_step')),
        'photo_base64': data.get('photo_base64', ''),
        'signature_base64': data.get('signature_base64', ''),
        'selected_subjects_json': pack_selected_subjects_json(
            data.get('selected_subjects') or data.get('SelectedSubjects') or [],
            data.get('bsc_subject_group') or data.get('BScSubjectGroup') or '',
        ),
        'nationality': data.get('nationality', 'Indian'),
        'religion': data.get('religion', ''),
        'marital_status': data.get('marital_status', ''),
        'blood_group': data.get('blood_group', ''),
        'status': status,
        'is_submitted': status == 'Submitted',
        'updated_date': timezone.now(),
    }
    if existing:
        if not defaults.get('photo_base64') and existing.photo_base64:
            defaults['photo_base64'] = existing.photo_base64
        if not defaults.get('signature_base64') and existing.signature_base64:
            defaults['signature_base64'] = existing.signature_base64

    if status == 'Submitted':
        if existing and existing.submitted_date:
            defaults['submitted_date'] = existing.submitted_date
        else:
            defaults['submitted_date'] = timezone.now()

    admission, _ = StudentAdmission.objects.update_or_create(
        application_no=app_no,
        defaults=defaults,
    )

    if status == 'Submitted':
        save_base64_image(defaults['photo_base64'], app_no, 'photo')
        save_base64_image(defaults['signature_base64'], app_no, 'signature')

    return admission