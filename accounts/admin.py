from django.contrib import admin

from .models import AdminUser, PasswordResetOTP, SocialMediaLink, Student


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