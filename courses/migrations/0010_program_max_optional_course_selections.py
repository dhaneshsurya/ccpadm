from django.db import migrations, models


def set_ba_first_semester_limit(apps, schema_editor):
    Program = apps.get_model('courses', 'Program')
    Program.objects.filter(program_name='B.A. First Semester').update(
        max_optional_course_selections=3,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_programcourse_auto_select'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='max_optional_course_selections',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text=(
                    'Maximum optional courses a student may select on the admission form '
                    '(e.g. 3 for B.A.). Compulsory and auto-selected lab papers do not count. '
                    'Leave blank for no limit.'
                ),
                null=True,
            ),
        ),
        migrations.RunPython(set_ba_first_semester_limit, migrations.RunPython.noop),
    ]