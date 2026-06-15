from django.db import models


class ProgramCourse(models.Model):
    """Maps to SQL Server Program_Courses table in courseinformation DB."""

    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    program_type = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=150, blank=True)
    course_name = models.CharField(max_length=250, blank=True)
    course_type_1 = models.CharField(max_length=50, blank=True)
    course_type_2 = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(null=True, blank=True)
    is_compulsory = models.BooleanField(
        default=False,
        help_text='Pre-select this subject as compulsory when students choose the program.',
    )
    auto_select_course = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='auto_selected_by_courses',
        help_text=(
            'Linked course auto-selected and locked when this course is checked '
            '(e.g. theory paper → practical/lab).'
        ),
    )
    subject_groups = models.ManyToManyField(
        'ProgramSubjectGroup',
        blank=True,
        related_name='courses',
        help_text='B.Sc. subject groups this course belongs to (for DSC group selection on admission).',
    )
    created_by = models.CharField(max_length=100, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    modified_by = models.CharField(max_length=100, blank=True)
    modified_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'Program_Courses'
        ordering = ['sort_order', 'legacy_id']

    def __str__(self):
        return f'{self.course_name} ({self.program_type})'


class Program(models.Model):
    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    program_code = models.CharField(max_length=50, blank=True)
    program_name = models.CharField(max_length=150)
    program_level = models.CharField(max_length=20, blank=True)
    is_nep_compliant = models.BooleanField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    max_optional_course_selections = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            'Maximum optional courses a student may select on the admission form '
            '(e.g. 3 for B.A.). Compulsory and auto-selected lab papers do not count. '
            'Leave blank for no limit.'
        ),
    )

    class Meta:
        db_table = 'Programs'

    def __str__(self):
        return self.program_name


class ProgramCourseInstruction(models.Model):
    """Custom guidance shown above the course table on the admission form."""

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='course_instructions',
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional short heading displayed in bold above the message.',
    )
    message = models.TextField(
        help_text='Instruction text for students selecting courses for this program.',
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Order when multiple instructions exist for the same program.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['program__program_name', 'sort_order', 'id']
        verbose_name = 'Course selection instruction'
        verbose_name_plural = 'Course selection instructions'

    def __str__(self):
        label = self.title.strip() or self.message.strip()[:60]
        return f'{self.program.program_name}: {label}'


class ProgramSubjectGroup(models.Model):
    """DSC subject groups for programs such as B.Sc. (used on the admission form)."""

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='subject_groups',
    )
    section_heading = models.CharField(
        max_length=150,
        help_text='e.g. B.Sc. Bio Group',
    )
    group_key = models.CharField(
        max_length=50,
        help_text='Unique key stored in applications, e.g. bio_a',
    )
    group_label = models.CharField(
        max_length=100,
        help_text='Short label shown to students, e.g. Group A',
    )
    departments = models.TextField(
        help_text='Comma-separated department names. DSC courses in these departments become compulsory when the group is selected.',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'section_heading', 'group_key']
        constraints = [
            models.UniqueConstraint(
                fields=['program', 'group_key'],
                name='unique_program_subject_group_key',
            ),
        ]
        verbose_name = 'Subject Group'
        verbose_name_plural = 'Subject Groups'

    def __str__(self):
        return f'{self.section_heading} — {self.group_label}'

    @property
    def department_list(self) -> list[str]:
        return [part.strip() for part in (self.departments or '').split(',') if part.strip()]

    @property
    def department_label(self) -> str:
        return ', '.join(self.department_list)

    @property
    def full_name(self) -> str:
        return f'{self.section_heading} — {self.group_label}'


class College(models.Model):
    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    college_name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'Colleges'
        verbose_name_plural = 'Colleges'

    def __str__(self):
        return self.college_name


class AcademicSession(models.Model):
    legacy_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    session_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'AcademicSessions'

    def __str__(self):
        return self.session_name