from django.db import migrations


def seed_default_instruction(apps, schema_editor):
    AdmissionSubmitInstruction = apps.get_model('admissions', 'AdmissionSubmitInstruction')
    if AdmissionSubmitInstruction.objects.exists():
        return
    AdmissionSubmitInstruction.objects.create(
        heading='Important — Before You Submit',
        notice=(
            'Please review your application carefully. Once submitted, you cannot edit your application.\n\n'
            'Ensure all personal details, educational records, course selections, and uploaded documents '
            'are correct before confirming submission.'
        ),
        sort_order=0,
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0003_admission_submit_instruction'),
    ]

    operations = [
        migrations.RunPython(seed_default_instruction, migrations.RunPython.noop),
    ]