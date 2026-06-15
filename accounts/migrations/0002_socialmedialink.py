from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialMediaLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(
                    choices=[
                        ('facebook', 'Facebook'),
                        ('instagram', 'Instagram'),
                        ('twitter', 'Twitter / X'),
                        ('youtube', 'YouTube'),
                        ('linkedin', 'LinkedIn'),
                        ('whatsapp', 'WhatsApp'),
                        ('website', 'Website'),
                    ],
                    max_length=30,
                )),
                ('url', models.URLField(max_length=500)),
                ('label', models.CharField(
                    blank=True,
                    help_text='Screen-reader label (defaults to platform name).',
                    max_length=100,
                )),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Social media link',
                'verbose_name_plural': 'Social media links',
                'ordering': ['sort_order', 'platform'],
            },
        ),
    ]