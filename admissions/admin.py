from django.contrib import admin
from django.utils.html import strip_tags

from .forms import AdmissionSubmitInstructionForm
from .models import (
    AdmissionSubmitInstruction,
    StudentAdmission,
    StudentDocument,
    StudentEducation,
)


@admin.register(StudentAdmission)
class StudentAdmissionAdmin(admin.ModelAdmin):
    list_display = ('application_no', 'reg_no', 'full_name', 'status', 'submitted_date')
    list_filter = ('status', 'program_type')
    search_fields = ('application_no', 'reg_no', 'full_name', 'email')


@admin.register(AdmissionSubmitInstruction)
class AdmissionSubmitInstructionAdmin(admin.ModelAdmin):
    form = AdmissionSubmitInstructionForm
    list_display = (
        'heading',
        'notice_preview',
        'sort_order',
        'is_active',
        'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('heading', 'notice')
    ordering = ('sort_order', 'id')
    fieldsets = (
        (None, {
            'fields': ('is_active', 'sort_order'),
        }),
        ('Submit popup', {
            'fields': ('heading', 'notice'),
            'description': (
                'This content appears in a popup when a student clicks '
                '"Submit Application" on the admission preview page.'
            ),
        }),
    )

    @admin.display(description='Notice preview')
    def notice_preview(self, obj):
        text = strip_tags(obj.notice or '').strip().replace('\n', ' ')
        if len(text) > 80:
            return f'{text[:80]}…'
        return text or '—'


admin.site.register(StudentEducation)
admin.site.register(StudentDocument)