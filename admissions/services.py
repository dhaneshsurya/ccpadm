import json
import tempfile
from datetime import datetime
from pathlib import Path

from .models import StudentAdmission

PRINTABLE_STATUSES = ('Submitted', 'Approved', 'Pending')
EDITABLE_STATUSES = ('Draft', 'Submitted', 'Pending')
LOCKED_STATUSES = ('Approved', 'Rejected')
ADMISSION_SESSION = '2026-27'


def get_declaration_context(admission):
    """Build placeholder values for declaration sections on print/preview."""
    gender = (getattr(admission, 'gender', '') or '').strip().lower()
    if gender == 'female':
        student_relation = 'D/o.'
    elif gender == 'male':
        student_relation = 'S/o.'
    else:
        student_relation = 'S/o. D/o.'

    father = (getattr(admission, 'father_name', '') or '').strip()
    mother = (getattr(admission, 'mother_name', '') or '').strip()
    guardian = father or mother

    if father:
        guardian_relation = 'F/o.'
    elif mother:
        guardian_relation = 'M/o.'
    else:
        guardian_relation = 'G/o.'

    student_name = (getattr(admission, 'full_name', '') or '').strip() or '-'
    guardian_name = guardian or '________________'

    submitted_dt = getattr(admission, 'submitted_date', None)
    signed_date = submitted_dt.strftime('%d-%m-%Y') if submitted_dt else datetime.now().strftime('%d-%m-%Y')

    return {
        'student_name': student_name,
        'guardian_name': guardian_name,
        'student_relation': student_relation,
        'guardian_relation': guardian_relation,
        'current_session': ADMISSION_SESSION,
        'enrolled_program': (getattr(admission, 'program_type', '') or '').strip() or '-',
        'signed_date': signed_date,
        'print_datetime': datetime.now().strftime('%d %b, %Y %H:%M:%S'),
    }


def _safe_image_src(base64_val):
    if not base64_val:
        return ''
    s = str(base64_val)
    if s.startswith('data:image'):
        return s
    return f'data:image/jpeg;base64,{s}'


def parse_selected_subjects_payload(raw):
    """Return (subjects list, optional B.Sc. group key) from stored JSON."""
    if not raw:
        return [], ''
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [], ''
    if isinstance(raw, dict):
        subjects = raw.get('subjects') or raw.get('items') or []
        group_key = (raw.get('bsc_subject_group') or raw.get('BScSubjectGroup') or '').strip()
        return subjects if isinstance(subjects, list) else [], group_key
    if isinstance(raw, list):
        return raw, ''
    return [], ''


def parse_selected_subjects(admission):
    if not admission or not admission.selected_subjects_json:
        return []
    subjects, _ = parse_selected_subjects_payload(admission.selected_subjects_json)
    return subjects


def pack_selected_subjects_json(subjects, bsc_subject_group=''):
    subjects = subjects or []
    group_key = (bsc_subject_group or '').strip()
    if group_key:
        return json.dumps({'bsc_subject_group': group_key, 'subjects': subjects})
    return json.dumps(subjects)


def _education_field(item, *keys, default=''):
    if not isinstance(item, dict):
        return default
    for key in keys:
        val = item.get(key)
        if val not in (None, ''):
            return val
    return default


def normalize_education_row(item, default_class=''):
    """Normalize JS/DB education keys for templates (preview, print, PDF)."""
    class_name = _education_field(
        item, 'className', 'ClassName', 'Class', 'class', default=default_class,
    )
    board = _education_field(item, 'board', 'Board')
    stream = _education_field(item, 'stream', 'Stream')
    duration = _education_field(item, 'duration', 'Duration')
    year = _education_field(item, 'year', 'Year')
    total = _education_field(item, 'totalMarks', 'TotalMarks', 'total_marks')
    obtained = _education_field(item, 'obtained', 'Obtained', 'obtainedMarks', 'obtained_marks')
    percentage = _education_field(item, 'percentage', 'Percentage')
    grade = _education_field(item, 'grade', 'Grade')

    if not any((class_name, board, stream, year, total, obtained, percentage, grade)):
        return None

    row = {
        'className': class_name or default_class or '-',
        'board': board or '-',
        'stream': stream or '-',
        'duration': str(duration) if duration not in (None, '') else '-',
        'year': str(year) if year not in (None, '') else '-',
        'totalMarks': str(total) if total not in (None, '') else '-',
        'obtained': str(obtained) if obtained not in (None, '') else '-',
        'percentage': str(percentage) if percentage not in (None, '') else '-',
        'grade': grade or '-',
        # Keep PascalCase aliases for form draft restore
        'ClassName': class_name or default_class or '',
        'Board': board or '',
        'Stream': stream or '',
        'Duration': str(duration) if duration not in (None, '') else '',
        'Year': str(year) if year not in (None, '') else '',
        'TotalMarks': str(total) if total not in (None, '') else '',
        'Obtained': str(obtained) if obtained not in (None, '') else '',
        'Percentage': str(percentage) if percentage not in (None, '') else '',
        'Grade': grade or '',
    }
    return row


def build_education_list(admission):
    raw_rows = []
    if admission.education_json:
        try:
            stored = json.loads(admission.education_json)
            if isinstance(stored, list) and stored:
                raw_rows = stored
        except (json.JSONDecodeError, TypeError):
            pass

    if not raw_rows:
        mappings = [
            ('10th', admission.class10, admission.board10, None, admission.duration10, admission.year10,
             admission.total_marks10, admission.obtained10, admission.percentage10, admission.grade10),
            ('12th', admission.class12, admission.board12, admission.stream12, admission.duration12,
             admission.year12, admission.total_marks12, admission.obtained12, admission.percentage12,
             admission.grade12),
            ('Graduation', admission.class_grad, admission.board_grad, admission.stream_grad,
             admission.duration_grad, admission.year_grad, admission.total_marks_grad,
             admission.obtained_grad, admission.percentage_grad, admission.grade_grad),
        ]
        for prefix, cls, board, stream, duration, year, total, obtained, pct, grade in mappings:
            if cls or board or stream:
                raw_rows.append({
                    'ClassName': cls or prefix,
                    'Board': board or '',
                    'Stream': stream or '',
                    'Duration': duration or '',
                    'Year': year or '',
                    'TotalMarks': total or '',
                    'Obtained': obtained or '',
                    'Percentage': pct or '',
                    'Grade': grade or '',
                })

    rows = []
    for item in raw_rows:
        default_class = _education_field(item, 'className', 'ClassName', 'Class', 'class')
        normalized = normalize_education_row(item, default_class=default_class)
        if normalized:
            rows.append(normalized)
    return rows


def _pick(primary, fallback=''):
    if primary not in (None, ''):
        return primary
    return fallback or ''


class AdmissionDisplay:
    """Read-only view of admission with student registration fallbacks for empty fields."""

    _STUDENT_FIELDS = {
        'full_name': 'full_name',
        'mobile': 'mobile',
        'email': 'email',
        'aadhaar': 'aadhaar',
        'program_type': 'program_type',
        'course_name': 'course_name',
    }

    def __init__(self, admission, student=None):
        self._admission = admission
        self._student = student

    def __getattr__(self, name):
        value = getattr(self._admission, name, None)
        if value not in (None, '') or not self._student:
            return value
        student_attr = self._STUDENT_FIELDS.get(name)
        if student_attr:
            return getattr(self._student, student_attr, '') or value
        return value


def admission_to_form_dict(admission, student=None):
    if not admission:
        return {}
    data = {
        'ApplicationNo': admission.application_no or '',
        'ProgramType': admission.program_type or '',
        'CourseName': admission.course_name or '',
        'Subject': admission.subject or '',
        'SelectedSubjects': parse_selected_subjects(admission),
        'BScSubjectGroup': parse_selected_subjects_payload(admission.selected_subjects_json)[1],
        'FullName': admission.full_name or '',
        'FatherName': admission.father_name or '',
        'MotherName': admission.mother_name or '',
        'Gender': admission.gender or '',
        'Category': admission.category or '',
        'Nationality': admission.nationality or 'Indian',
        'Religion': admission.religion or '',
        'MaritalStatus': admission.marital_status or '',
        'BloodGroup': admission.blood_group or '',
        'DOB': admission.dob.strftime('%Y-%m-%d') if admission.dob else '',
        'Mobile': admission.mobile or '',
        'Email': admission.email or '',
        'Aadhaar': admission.aadhaar or '',
        'Apaar': admission.apaar_id or '',
        'HasDisability': 1 if admission.has_disability else 0,
        'DisabilityDetails': admission.disability_details or '',
        'DisabilityPercentage': admission.disability_percentage or '',
        'DisabilityType': admission.disability_type or '',
        'Minority': 'Yes' if admission.is_minority else 'No',
        'Medium': admission.medium or '',
        'PermState': admission.perm_state or '',
        'PermDistrict': admission.perm_district or '',
        'PermCity': admission.perm_city or '',
        'PermVillage': admission.perm_village or '',
        'PermPinCode': admission.perm_pin_code or '',
        'CorrState': admission.corr_state or '',
        'CorrDistrict': admission.corr_district or '',
        'CorrCity': admission.corr_city or '',
        'CorrVillage': admission.corr_village or '',
        'CorrPinCode': admission.corr_pin_code or '',
        'PhotoBase64': admission.photo_base64 or '',
        'SignatureBase64': admission.signature_base64 or '',
        'Education': build_education_list(admission),
        'ActiveStep': admission.active_step if admission.active_step is not None else 0,
        'WizardVersion': 2,
    }
    if student:
        data['FullName'] = _pick(data['FullName'], student.full_name)
        data['Mobile'] = _pick(data['Mobile'], student.mobile)
        data['Email'] = _pick(data['Email'], student.email)
        data['Aadhaar'] = _pick(data['Aadhaar'], student.aadhaar)
        data['ProgramType'] = _pick(data['ProgramType'], student.program_type)
        data['CourseName'] = _pick(data['CourseName'], student.course_name)
    return data


def normalize_form_payload(data):
    """Map JS camelCase payload to snake_case for save_admission_from_form."""

    def g(*keys, default=''):
        for k in keys:
            if k in data and data[k] not in (None, ''):
                return data[k]
        return default

    education = []
    for key in ('Education', 'education'):
        if key not in data:
            continue
        raw = data[key]
        if isinstance(raw, list):
            education = raw
            break
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    education = parsed
                    break
            except json.JSONDecodeError:
                pass

    selected_raw = g('selected_subjects', 'SelectedSubjects', default=[])
    if isinstance(selected_raw, str):
        try:
            selected_raw = json.loads(selected_raw)
        except json.JSONDecodeError:
            selected_raw = []
    selected, stored_group = parse_selected_subjects_payload(selected_raw)
    bsc_subject_group = g('bsc_subject_group', 'BScSubjectGroup', default=stored_group)

    subject_str = g('subject', 'Subject')
    if not subject_str and selected:
        subject_str = ', '.join(
            s.get('name', '') for s in selected if isinstance(s, dict)
        )

    return {
        'application_no': g('application_no', 'ApplicationNo'),
        'program_type': g('program_type', 'ProgramType'),
        'course_name': g('course_name', 'CourseName'),
        'subject': subject_str,
        'selected_subjects': selected,
        'bsc_subject_group': bsc_subject_group,
        'full_name': g('full_name', 'FullName'),
        'father_name': g('father_name', 'FatherName'),
        'mother_name': g('mother_name', 'MotherName'),
        'gender': g('gender', 'Gender'),
        'category': g('category', 'Category'),
        'nationality': g('nationality', 'Nationality', default='Indian'),
        'religion': g('religion', 'Religion'),
        'marital_status': g('marital_status', 'MaritalStatus'),
        'blood_group': g('blood_group', 'BloodGroup'),
        'dob': g('dob', 'DOB'),
        'mobile': g('mobile', 'Mobile'),
        'email': g('email', 'Email'),
        'aadhaar': g('aadhaar', 'Aadhaar'),
        'apaar': g('apaar', 'Apaar', 'APAARId'),
        'has_disability': g('has_disability', 'HasDisability') in (1, '1', True, 'yes', 'Yes'),
        'disability_details': g('disability_details', 'DisabilityDetails'),
        'disability_percentage': g('disability_percentage', 'DisabilityPercentage'),
        'disability_type': g('disability_type', 'DisabilityType'),
        'minority': g('minority', 'Minority', 'IsMinority'),
        'medium': g('medium', 'Medium'),
        'perm_state': g('perm_state', 'PermState'),
        'perm_district': g('perm_district', 'PermDistrict'),
        'perm_city': g('perm_city', 'PermCity'),
        'perm_village': g('perm_village', 'PermVillage'),
        'perm_pin_code': g('perm_pin_code', 'PermPinCode'),
        'corr_state': g('corr_state', 'CorrState'),
        'corr_district': g('corr_district', 'CorrDistrict'),
        'corr_city': g('corr_city', 'CorrCity'),
        'corr_village': g('corr_village', 'CorrVillage'),
        'corr_pin_code': g('corr_pin_code', 'CorrPinCode'),
        'photo_base64': g('photo_base64', 'PhotoBase64'),
        'signature_base64': g('signature_base64', 'SignatureBase64'),
        'education': education,
        'active_step': (
            data['ActiveStep'] if 'ActiveStep' in data and data['ActiveStep'] is not None
            else data.get('active_step') if 'active_step' in data and data.get('active_step') is not None
            else ''
        ),
    }


def get_editable_admission(reg_no, app_no=None):
    """Return the student's application that can still be edited or re-saved."""
    qs = StudentAdmission.objects.filter(reg_no=reg_no, status__in=EDITABLE_STATUSES)
    if app_no:
        return qs.filter(application_no=app_no).first()
    return qs.order_by('-updated_date', '-created_date').first()


def is_admission_locked(reg_no):
    return StudentAdmission.objects.filter(reg_no=reg_no, status__in=LOCKED_STATUSES).exists()


def resolve_save_status(reg_no, app_no):
    if app_no:
        existing = StudentAdmission.objects.filter(application_no=app_no, reg_no=reg_no).first()
        if existing and existing.status == 'Submitted':
            return 'Submitted'
    return 'Draft'


def get_printable_admission(reg_no, app_no=None):
    """Return the student's submitted/approved application for print and PDF."""
    qs = StudentAdmission.objects.filter(reg_no=reg_no)
    if app_no:
        return qs.filter(application_no=app_no).first()
    return (
        qs.filter(status__in=PRINTABLE_STATUSES)
        .order_by('-submitted_date', '-updated_date', '-created_date')
        .first()
    )


def build_submit_payload(reg_no, data, generate_app_no):
    """Merge posted submit data with the saved draft so fields are not wiped."""
    data = data or {}
    app_no = data.get('application_no') or data.get('ApplicationNo')

    draft = None
    if app_no:
        draft = StudentAdmission.objects.filter(application_no=app_no, reg_no=reg_no).first()
    if not draft:
        draft = get_editable_admission(reg_no)

    base = normalize_form_payload(admission_to_form_dict(draft)) if draft else {}
    incoming = normalize_form_payload(data)
    payload = dict(base)
    for key, value in incoming.items():
        if value not in (None, '', [], {}):
            payload[key] = value

    if not payload.get('application_no'):
        payload['application_no'] = (
            app_no
            or (draft.application_no if draft else None)
            or generate_app_no()
        )
    return payload, draft


def get_print_context(admission, student=None):
    """Build template context for print/PDF views."""
    if student is None and admission.reg_no:
        from accounts.models import Student
        student = Student.objects.filter(registration_no=admission.reg_no).first()

    display_admission = AdmissionDisplay(admission, student)
    education = build_education_list(admission)
    selected_subjects = parse_selected_subjects(admission)
    dob_display = admission.dob.strftime('%d/%m/%Y') if admission.dob else '-'
    submitted_display = ''
    if admission.submitted_date:
        submitted_display = admission.submitted_date.strftime('%A, %d.%m.%Y, %H:%M:%S')

    declaration = get_declaration_context(display_admission)

    return {
        'admission': display_admission,
        'education': education,
        'selected_subjects': selected_subjects,
        'photo_src': _safe_image_src(admission.photo_base64),
        'sign_src': _safe_image_src(admission.signature_base64),
        'dob_display': dob_display,
        'submitted_display': submitted_display,
        'has_disability': bool(admission.has_disability),
        'is_minority': 'Yes' if admission.is_minority else 'No',
        'print_time': datetime.now().strftime('%A, %d.%m.%Y %H:%M:%S'),
        **declaration,
    }


def get_application_lock_message(status):
    if status == 'Approved':
        return 'Your application has been approved. You cannot edit it anymore.'
    if status == 'Rejected':
        return 'Your application has been rejected. You cannot edit it anymore.'
    return ''


def get_application_print_view_context(admission, *, preview_mode=False):
    """Shared context for preview, print, and PDF views."""
    context = get_print_context(admission)
    context['preview_mode'] = preview_mode
    context['can_submit'] = preview_mode and admission.status not in PRINTABLE_STATUSES
    context['can_download_pdf'] = admission.status in PRINTABLE_STATUSES
    context['can_edit_application'] = admission.status not in LOCKED_STATUSES
    context['application_lock_message'] = get_application_lock_message(admission.status)
    return context


def write_image_for_pdf(base64_val, prefix):
    """Write base64 image to a temp file for xhtml2pdf rendering."""
    if not base64_val:
        return ''
    src = _safe_image_src(base64_val)
    if not src.startswith('data:image'):
        return src

    header, encoded = src.split(',', 1)
    suffix = '.png' if 'png' in header.lower() else '.jpg'
    try:
        import base64
        image_bytes = base64.b64decode(encoded)
    except Exception:
        return ''

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix=prefix)
    tmp.write(image_bytes)
    tmp.close()
    return str(Path(tmp.name).resolve())