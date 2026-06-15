from django.db import migrations


def seed_bsc_groups(apps, schema_editor):
    Program = apps.get_model('courses', 'Program')
    ProgramSubjectGroup = apps.get_model('courses', 'ProgramSubjectGroup')

    defaults = (
        ('B.Sc. Bio Group', 'bio_a', 'Group A', 'Chemistry, Botany, Zoology', 0),
        ('B.Sc. Bio Group', 'bio_b', 'Group B', 'Chemistry, Forestry, Zoology', 1),
        ('B.Sc. Maths Group', 'maths_a', 'Group A', 'Chemistry, Mathematics, Physics', 2),
        ('B.Sc. Maths Group', 'maths_b', 'Group B', 'Computer Science, Mathematics, Physics', 3),
    )

    for program in Program.objects.all():
        name = (program.program_name or '').strip()
        if not name.lower().startswith('b.sc'):
            continue
        if ProgramSubjectGroup.objects.filter(program=program).exists():
            continue
        for section_heading, group_key, group_label, departments, sort_order in defaults:
            ProgramSubjectGroup.objects.create(
                program=program,
                section_heading=section_heading,
                group_key=group_key,
                group_label=group_label,
                departments=departments,
                sort_order=sort_order,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_program_subject_group'),
    ]

    operations = [
        migrations.RunPython(seed_bsc_groups, migrations.RunPython.noop),
    ]