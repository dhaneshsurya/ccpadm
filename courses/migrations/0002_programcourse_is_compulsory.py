from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='programcourse',
            name='is_compulsory',
            field=models.BooleanField(
                default=False,
                help_text='Pre-select this subject as compulsory when students choose the program.',
            ),
        ),
    ]