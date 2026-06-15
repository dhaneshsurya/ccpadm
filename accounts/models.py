import uuid

from django.db import models


class Student(models.Model):
    """Maps to SQL Server Students table."""

    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    registration_no = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=300, blank=True)
    email = models.EmailField(max_length=256, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    aadhaar = models.CharField(max_length=20, blank=True, null=True)
    user_id = models.UUIDField(default=uuid.uuid4, editable=False)
    program_type = models.CharField(max_length=200, blank=True)
    course_name = models.CharField(max_length=200, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'Students'
        ordering = ['-created_date']

    def __str__(self):
        return f'{self.registration_no} - {self.full_name}'


class AdminUser(models.Model):
    """Maps to SQL Server AdminUsers table."""

    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    reset_key = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'AdminUsers'

    def __str__(self):
        return self.username


class SocialMediaLink(models.Model):
    """Social profile URLs shown in the site footer (editable in Django admin)."""

    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter / X'),
        ('youtube', 'YouTube'),
        ('linkedin', 'LinkedIn'),
        ('whatsapp', 'WhatsApp'),
        ('website', 'Website'),
    ]

    PLATFORM_ICONS = {
        'facebook': 'fab fa-facebook-f',
        'instagram': 'fab fa-instagram',
        'twitter': 'fab fa-x-twitter',
        'youtube': 'fab fa-youtube',
        'linkedin': 'fab fa-linkedin-in',
        'whatsapp': 'fab fa-whatsapp',
        'website': 'fas fa-globe',
    }

    platform = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    url = models.URLField(max_length=500)
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text='Screen-reader label (defaults to platform name).',
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'platform']
        verbose_name = 'Social media link'
        verbose_name_plural = 'Social media links'

    def __str__(self):
        return f'{self.get_platform_display()} — {self.url}'

    @property
    def icon_class(self):
        return self.PLATFORM_ICONS.get(self.platform, 'fas fa-link')

    @property
    def accessible_label(self):
        return self.label.strip() or self.get_platform_display()


class PasswordResetOTP(models.Model):
    """Maps to SQL Server PasswordResetOTP table."""

    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    email = models.EmailField(max_length=255)
    otp_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'PasswordResetOTP'
        ordering = ['-created_at']