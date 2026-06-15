from django.db import models


class StudentAdmission(models.Model):
    """Maps to SQL Server StudentAdmission table."""

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending', 'Pending'),
        ('Submitted', 'Submitted'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    application_no = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    reg_no = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    program_type = models.CharField(max_length=50, blank=True)
    course_name = models.CharField(max_length=100, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    father_name = models.CharField(max_length=150, blank=True)
    mother_name = models.CharField(max_length=150, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    category = models.CharField(max_length=20, blank=True)
    nationality = models.CharField(max_length=50, blank=True)
    religion = models.CharField(max_length=50, blank=True)
    marital_status = models.CharField(max_length=20, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    dob = models.DateField(null=True, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    email = models.CharField(max_length=100, blank=True)
    aadhaar = models.CharField(max_length=12, blank=True)
    apaar_id = models.CharField(max_length=20, blank=True)
    has_disability = models.BooleanField(null=True, blank=True)
    disability_details = models.CharField(max_length=255, blank=True)
    disability_percentage = models.CharField(max_length=10, blank=True)
    disability_type = models.CharField(max_length=100, blank=True)
    is_minority = models.BooleanField(null=True, blank=True)
    medium = models.CharField(max_length=20, blank=True)

    perm_state = models.CharField(max_length=100, blank=True)
    perm_district = models.CharField(max_length=100, blank=True)
    perm_city = models.CharField(max_length=100, blank=True)
    perm_village = models.CharField(max_length=150, blank=True)
    perm_pin_code = models.CharField(max_length=10, blank=True)
    corr_state = models.CharField(max_length=100, blank=True)
    corr_district = models.CharField(max_length=100, blank=True)
    corr_city = models.CharField(max_length=100, blank=True)
    corr_village = models.CharField(max_length=150, blank=True)
    corr_pin_code = models.CharField(max_length=10, blank=True)

    class10 = models.CharField(max_length=50, blank=True)
    board10 = models.CharField(max_length=150, blank=True)
    duration10 = models.IntegerField(null=True, blank=True)
    year10 = models.IntegerField(null=True, blank=True)
    total_marks10 = models.CharField(max_length=50, blank=True)
    obtained10 = models.CharField(max_length=50, blank=True)
    percentage10 = models.CharField(max_length=10, blank=True)
    grade10 = models.CharField(max_length=20, blank=True)

    class12 = models.CharField(max_length=50, blank=True)
    board12 = models.CharField(max_length=150, blank=True)
    duration12 = models.IntegerField(null=True, blank=True)
    year12 = models.IntegerField(null=True, blank=True)
    total_marks12 = models.CharField(max_length=50, blank=True)
    obtained12 = models.CharField(max_length=50, blank=True)
    percentage12 = models.CharField(max_length=10, blank=True)
    grade12 = models.CharField(max_length=20, blank=True)

    class_grad = models.CharField(max_length=50, blank=True)
    board_grad = models.CharField(max_length=150, blank=True)
    duration_grad = models.IntegerField(null=True, blank=True)
    year_grad = models.IntegerField(null=True, blank=True)
    total_marks_grad = models.CharField(max_length=50, blank=True)
    obtained_grad = models.CharField(max_length=50, blank=True)
    percentage_grad = models.CharField(max_length=10, blank=True)
    grade_grad = models.CharField(max_length=20, blank=True)
    stream12 = models.CharField(max_length=20, blank=True)
    stream_grad = models.CharField(max_length=20, blank=True)
    education_json = models.TextField(blank=True, null=True)
    active_step = models.IntegerField(null=True, blank=True)

    photo_base64 = models.TextField(blank=True, null=True)
    signature_base64 = models.TextField(blank=True, null=True)
    selected_subjects_json = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, default='Draft')
    is_submitted = models.BooleanField(null=True, blank=True)
    is_approved = models.BooleanField(null=True, blank=True)
    is_rejected = models.BooleanField(null=True, blank=True)
    remarks = models.CharField(max_length=500, blank=True)
    approved_by = models.CharField(max_length=100, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    rejected_by = models.CharField(max_length=100, blank=True)
    rejected_date = models.DateTimeField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)
    submitted_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'StudentAdmission'
        ordering = ['-submitted_date', '-created_date']

    def __str__(self):
        return self.application_no or f'Admission #{self.pk}'


class StudentEducation(models.Model):
    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    application_no = models.CharField(max_length=50, blank=True)
    exam_level = models.CharField(max_length=20, blank=True)
    class_name = models.CharField(max_length=50, blank=True)
    board = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=20, blank=True)
    year_of_passing = models.CharField(max_length=20, blank=True)
    total_marks = models.CharField(max_length=20, blank=True)
    marks_obtained = models.CharField(max_length=20, blank=True)
    percentage = models.CharField(max_length=20, blank=True)
    grade = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'StudentEducation'


class StudentDocument(models.Model):
    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    application_no = models.CharField(max_length=50, blank=True)
    photo_verified = models.BooleanField(null=True, blank=True)
    aadhar_verified = models.BooleanField(null=True, blank=True)
    signature_verified = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = 'StudentDocuments'