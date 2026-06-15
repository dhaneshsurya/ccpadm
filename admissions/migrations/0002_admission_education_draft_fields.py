from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentadmission',
            name='stream12',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='studentadmission',
            name='stream_grad',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='studentadmission',
            name='education_json',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentadmission',
            name='active_step',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]