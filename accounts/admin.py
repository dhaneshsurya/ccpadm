from django.contrib import admin
from django.utils.html import format_html

from .forms import (
    HelpdeskIssueAdminForm,
    HelpdeskOfficerAdminForm,
    ImportantInstructionAdminForm,
    NoticeAdminForm,
)
from .models import (
    AdminUser,
    HelpdeskIssue,
    HelpdeskOfficer,
    ImportantInstruction,
    Notice,
    PasswordResetOTP,
    SocialMediaLink,
    Student,
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'full_name', 'email', 'mobile', 'program_type', 'created_date')
    search_fields = ('registration_no', 'full_name', 'email', 'mobile')


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('username',)


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'expiry_at', 'is_used')


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ('platform', 'url', 'label', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('platform', 'is_active')
    search_fields = ('url', 'label')
    ordering = ('sort_order', 'platform')
    fieldsets = (
        (None, {
            'fields': ('platform', 'url', 'label', 'sort_order', 'is_active'),
        }),
    )


@admin.register(ImportantInstruction)
class ImportantInstructionAdmin(admin.ModelAdmin):
    form = ImportantInstructionAdminForm
    list_display = ('title', 'sort_order', 'is_active', 'has_file', 'updated_at')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('sort_order', '-created_at')
    readonly_fields = ('created_at', 'updated_at', 'attachment_link')
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'attached_file', 'attachment_link'),
        }),
        ('Display', {
            'fields': ('sort_order', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(boolean=True, description='File')
    def has_file(self, obj):
        return obj.has_attachment

    @admin.display(description='Current attachment')
    def attachment_link(self, obj):
        if obj.pk and obj.attached_file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">{}</a>',
                obj.attached_file.url,
                obj.attached_file.name,
            )
        return '—'


@admin.register(HelpdeskOfficer)
class HelpdeskOfficerAdmin(admin.ModelAdmin):
    form = HelpdeskOfficerAdminForm
    list_display = ('name', 'designation', 'department', 'phone', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active', 'department')
    search_fields = ('name', 'designation', 'department', 'phone', 'email')
    ordering = ('sort_order', 'name')
    fieldsets = (
        ('Officer details', {
            'fields': ('name', 'designation', 'department'),
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'office_hours'),
        }),
        ('Display', {
            'fields': ('sort_order', 'is_active'),
        }),
    )


@admin.register(HelpdeskIssue)
class HelpdeskIssueAdmin(admin.ModelAdmin):
    form = HelpdeskIssueAdminForm
    list_display = ('subject', 'name', 'email', 'mobile', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'name', 'email', 'mobile', 'registration_no', 'message')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Submitter', {
            'fields': ('name', 'email', 'mobile', 'registration_no'),
        }),
        ('Issue', {
            'fields': ('subject', 'message', 'status'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    form = NoticeAdminForm
    list_display = ('title', 'sort_order', 'is_active', 'expires_at', 'has_file', 'updated_at')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('sort_order', '-created_at')
    readonly_fields = ('created_at', 'updated_at', 'attachment_link')
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'attached_file', 'attachment_link'),
        }),
        ('Display', {
            'fields': ('sort_order', 'is_active', 'expires_at'),
            'description': 'Notices appear in the scrolling banner on the home page.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(boolean=True, description='File')
    def has_file(self, obj):
        return obj.has_attachment

    @admin.display(description='Current attachment')
    def attachment_link(self, obj):
        if obj.pk and obj.attached_file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">{}</a>',
                obj.attached_file.url,
                obj.attached_file.name,
            )
        return '—'