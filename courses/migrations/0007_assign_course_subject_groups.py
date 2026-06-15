from django.db import migrations


def assign_groups_from_departments(apps, schema_editor):
    ProgramCourse = apps.get_model('courses', 'ProgramCourse')
    ProgramSubjectGroup = apps.get_model('courses', 'ProgramSubjectGroup')

    for course in ProgramCourse.objects.filter(program_type__iregex=r'^b\.sc'):
        if course.subject_groups.exists():
            continue
        if (course.course_type_2 or '').strip().upper() != 'DSC':
            continue
        department = (course.department or '').strip()
        if not department:
            continue
        matches = []
        for group in ProgramSubjectGroup.objects.filter(program__program_name=course.program_type):
            departments = [part.strip() for part in (group.departments or '').split(',') if part.strip()]
            if department in departments:
                matches.append(group)
        if matches:
            course.subject_groups.set(matches)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_programcourse_subject_groups'),
    ]

    operations = [
        migrations.RunPython(assign_groups_from_departments, migrations.RunPython.noop),
    ]