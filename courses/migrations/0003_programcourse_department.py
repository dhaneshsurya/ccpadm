from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_programcourse_is_compulsory'),
    ]

    operations = [
        migrations.AddField(
            model_name='programcourse',
            name='department',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]