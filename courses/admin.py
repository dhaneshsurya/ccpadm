from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .forms import ProgramCourseInstructionForm
from .models import (
    AcademicSession,
    College,
    Program,
    ProgramCourse,
    ProgramCourseInstruction,
    ProgramSubjectGroup,
)
from .subject_groups import (
    group_label_for_course,
    is_bsc_program,
    seed_default_bsc_groups_for_program,
)

_TH = 'padding:8px;border-bottom:1px solid #ddd;background:#f8f8f8;text-align:left;'
_TD = 'padding:8px;border-bottom:1px solid #ddd;'
_COURSE_ROW_BSC = (
    '<tr>'
    f'<td style="{_TD}"><a href="{{}}">{{}}</a></td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    '</tr>'
)
_COURSE_ROW = (
    '<tr>'
    f'<td style="{_TD}"><a href="{{}}">{{}}</a></td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    f'<td style="{_TD}">{{}}</td>'
    '</tr>'
)


class ProgramSubjectGroupInline(admin.TabularInline):
    model = ProgramSubjectGroup
    extra = 1
    fields = ('sort_order', 'section_heading', 'group_key', 'group_label', 'departments')
    ordering = ('sort_order', 'section_heading', 'group_key')
    verbose_name = 'Subject group'
    verbose_name_plural = (
        'B.Sc. Subject Groups — edit rows below, then click Save. '
        'Students choose one group on the admission form; DSC courses in that group become compulsory.'
    )


class ProgramCourseInstructionInline(admin.StackedInline):
    model = ProgramCourseInstruction
    form = ProgramCourseInstructionForm
    extra = 0
    fields = ('is_active', 'sort_order', 'title', 'message')
    ordering = ('sort_order', 'id')
    verbose_name = 'Course selection instruction'
    verbose_name_plural = (
        'Admission form instructions — shown above the course table when students select this program.'
    )


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        'program_name',
        'program_code',
        'program_level',
        'is_active',
        'max_optional_course_selections',
        'course_count',
        'subject_group_count',
    )
    list_filter = ('program_level', 'is_active', 'is_nep_compliant')
    search_fields = ('program_name', 'program_code')
    readonly_fields = ('related_courses_panel',)

    def get_inlines(self, request, obj=None):
        if not obj:
            return ()
        inlines = [ProgramCourseInstructionInline]
        if is_bsc_program(obj.program_name):
            inlines.append(ProgramSubjectGroupInline)
        return tuple(inlines)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return ('related_courses_panel',)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                (None, {
                    'fields': (
                        'program_name',
                        'program_code',
                        'program_level',
                        'is_nep_compliant',
                        'is_active',
                        'max_optional_course_selections',
                        'legacy_id',
                    ),
                }),
            )
        return (
            (None, {
                'fields': (
                    'program_name',
                    'program_code',
                    'program_level',
                    'is_nep_compliant',
                    'is_active',
                    'max_optional_course_selections',
                    'legacy_id',
                ),
            }),
            ('Related Courses', {
                'fields': ('related_courses_panel',),
                'classes': ('wide',),
            }),
        )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and is_bsc_program(obj.program_name):
            seed_default_bsc_groups_for_program(obj)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description='Courses')
    def course_count(self, obj):
        return ProgramCourse.objects.filter(program_type=obj.program_name).count()

    @admin.display(description='Groups')
    def subject_group_count(self, obj):
        if not is_bsc_program(obj.program_name):
            return '—'
        return obj.subject_groups.count()

    @admin.display(description='Courses linked to this program')
    def related_courses_panel(self, obj):
        if not obj or not obj.pk:
            return 'Save the program first to see linked courses.'

        courses = ProgramCourse.objects.filter(program_type=obj.program_name).order_by(
            'sort_order', 'course_name',
        )
        show_groups = is_bsc_program(obj.program_name)
        add_url = (
            reverse('admin:courses_programcourse_add')
            + f'?program_type={obj.program_name}'
        )
        changelist_url = (
            reverse('admin:courses_programcourse_changelist')
            + f'?program_type__exact={obj.program_name}'
        )

        if not courses.exists():
            return format_html(
                '<p class="help">No courses linked to <strong>{}</strong>.</p>'
                '<p><a class="button" href="{}">Add course</a></p>',
                obj.program_name,
                add_url,
            )

        if show_groups:
            rows = format_html_join(
                '',
                _COURSE_ROW_BSC,
                (
                    (
                        reverse('admin:courses_programcourse_change', args=[c.pk]),
                        c.course_name,
                        c.department or '—',
                        group_label_for_course(
                            c.department, c.course_type_2, obj.program_name, course=c,
                        ) or '—',
                        c.course_type_1 or '—',
                        c.course_type_2 or '—',
                        'Yes' if c.is_compulsory else '—',
                    )
                    for c in courses
                ),
            )
            header = format_html(
                '<tr>'
                f'<th style="{_TH}">Course Name</th>'
                f'<th style="{_TH}">Department</th>'
                f'<th style="{_TH}">Subject Group</th>'
                f'<th style="{_TH}">Type 1</th>'
                f'<th style="{_TH}">Type 2</th>'
                f'<th style="{_TH}">Compulsory</th>'
                '</tr>',
            )
        else:
            rows = format_html_join(
                '',
                _COURSE_ROW,
                (
                    (
                        reverse('admin:courses_programcourse_change', args=[c.pk]),
                        c.course_name,
                        c.department or '—',
                        c.course_type_1 or '—',
                        c.course_type_2 or '—',
                        'Yes' if c.is_compulsory else '—',
                    )
                    for c in courses
                ),
            )
            header = format_html(
                '<tr>'
                f'<th style="{_TH}">Course Name</th>'
                f'<th style="{_TH}">Department</th>'
                f'<th style="{_TH}">Type 1</th>'
                f'<th style="{_TH}">Type 2</th>'
                f'<th style="{_TH}">Compulsory</th>'
                '</tr>',
            )

        preview = ''
        if show_groups and obj.subject_groups.exists():
            preview_rows = format_html_join(
                '',
                '<li><strong>{}</strong> (<code>{}</code>) — {}</li>',
                (
                    (g.full_name, g.group_key, g.department_label)
                    for g in obj.subject_groups.order_by('sort_order', 'section_heading', 'group_key')
                ),
            )
            preview = format_html(
                '<p style="margin:0 0 10px;color:#1e3a8a;">'
                '<strong>Current groups</strong> (edit in the table below the form, then Save):</p>'
                '<ul style="margin:0 0 12px 18px;">{}</ul>',
                preview_rows,
            )

        return format_html(
            '<div class="program-related-courses">'
            '{}'
            '<p><strong>{} course(s)</strong> where <code>program_type</code> = <code>{}</code></p>'
            '<p>'
            '<a class="button" href="{}">View all in list</a> '
            '<a class="button" href="{}">Add course</a>'
            '</p>'
            '<table style="width:100%;border-collapse:collapse;margin-top:8px;">'
            '<thead>{}</thead>'
            '<tbody>{}</tbody>'
            '</table>'
            '</div>',
            preview,
            courses.count(),
            obj.program_name,
            changelist_url,
            add_url,
            header,
            rows,
        )


@admin.register(ProgramSubjectGroup)
class ProgramSubjectGroupAdmin(admin.ModelAdmin):
    list_display = (
        'program',
        'section_heading',
        'group_key',
        'group_label',
        'department_label',
        'sort_order',
    )
    list_filter = ('section_heading', 'program')
    search_fields = ('group_key', 'group_label', 'section_heading', 'departments', 'program__program_name')
    ordering = ('program__program_name', 'sort_order', 'section_heading', 'group_key')

    @admin.display(description='Departments')
    def department_label(self, obj):
        return obj.department_label


@admin.register(ProgramCourse)
class ProgramCourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_name',
        'program_type',
        'department',
        'auto_select_course',
        'subject_group_display',
        'course_type_1',
        'course_type_2',
        'is_compulsory',
        'sort_order',
    )
    list_filter = ('program_type', 'course_type_1', 'course_type_2', 'is_compulsory')
    search_fields = ('course_name', 'program_type', 'department')
    ordering = ('program_type', 'sort_order', 'course_name')
    raw_id_fields = ('auto_select_course',)
    fieldsets = (
        (None, {
            'fields': (
                'program_type',
                'department',
                'course_name',
                'course_type_1',
                'course_type_2',
                'sort_order',
                'is_compulsory',
                'auto_select_course',
            ),
        }),
        ('B.Sc. groups', {
            'fields': ('subject_groups',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Subject Group')
    def subject_group_display(self, obj):
        if not is_bsc_program(obj.program_type):
            return '—'
        label = group_label_for_course(
            obj.department, obj.course_type_2, obj.program_type, course=obj,
        )
        return label or '—'

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        program_type = request.GET.get('program_type', '').strip()
        if program_type:
            initial['program_type'] = program_type
        return initial


@admin.register(ProgramCourseInstruction)
class ProgramCourseInstructionAdmin(admin.ModelAdmin):
    form = ProgramCourseInstructionForm
    list_display = (
        'program',
        'title',
        'message_preview',
        'sort_order',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active', 'program__program_level', 'program__is_active')
    search_fields = ('program__program_name', 'title', 'message')
    autocomplete_fields = ('program',)
    ordering = ('program__program_name', 'sort_order', 'id')
    fieldsets = (
        (None, {
            'fields': ('program', 'is_active', 'sort_order'),
        }),
        ('Instruction', {
            'fields': ('title', 'message'),
            'description': (
                'This text appears on the admission form above the course table '
                'when a student selects the chosen program.'
            ),
        }),
    )

    @admin.display(description='Message preview')
    def message_preview(self, obj):
        text = (obj.message or '').strip().replace('\n', ' ')
        if len(text) > 80:
            return f'{text[:80]}…'
        return text or '—'


admin.site.register(College)
admin.site.register(AcademicSession)