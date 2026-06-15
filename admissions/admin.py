from django.contrib import admin

from .models import StudentAdmission, StudentDocument, StudentEducation


@admin.register(StudentAdmission)
class StudentAdmissionAdmin(admin.ModelAdmin):
    list_display = ('application_no', 'reg_no', 'full_name', 'status', 'submitted_date')
    list_filter = ('status', 'program_type')
    search_fields = ('application_no', 'reg_no', 'full_name', 'email')


admin.site.register(StudentEducation)
admin.site.register(StudentDocument)