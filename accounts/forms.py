from django_ckeditor_5.widgets import CKEditor5Widget
from django import forms

from .models import HelpdeskIssue, HelpdeskOfficer, ImportantInstruction, Notice
from .rich_text import clean_rich_text


class ImportantInstructionAdminForm(forms.ModelForm):
    class Meta:
        model = ImportantInstruction
        fields = ('title', 'description', 'attached_file', 'sort_order', 'is_active')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'vTextField',
                'size': 80,
                'placeholder': 'e.g. Document checklist for admission',
            }),
            'description': CKEditor5Widget(config_name='full'),
            'sort_order': forms.NumberInput(attrs={'min': 0, 'style': 'width: 6rem;'}),
        }
        help_texts = {
            'description': 'Rich text with full formatting. Shown on the home page.',
            'sort_order': 'Lower numbers appear first.',
            'attached_file': 'Supported: PDF, DOC, DOCX, JPG, PNG (max 10 MB).',
        }

    def clean_description(self):
        return clean_rich_text(self.cleaned_data.get('description'), field_label='Description')


class NoticeAdminForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = (
            'title',
            'description',
            'attached_file',
            'sort_order',
            'is_active',
            'expires_at',
        )
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'vTextField',
                'size': 80,
                'placeholder': 'e.g. Last date for form submission',
            }),
            'description': CKEditor5Widget(config_name='full'),
            'sort_order': forms.NumberInput(attrs={'min': 0, 'style': 'width: 6rem;'}),
            'expires_at': forms.SplitDateTimeWidget(),
        }
        help_texts = {
            'description': 'Rich text with full formatting. Shown in the scrolling notice banner.',
            'sort_order': 'Lower numbers appear first in the ticker.',
            'attached_file': 'Supported: PDF, DOC, DOCX, JPG, PNG (max 10 MB).',
            'expires_at': 'Leave blank to keep the notice visible until manually disabled.',
        }

    def clean_description(self):
        return clean_rich_text(self.cleaned_data.get('description'), field_label='Description')


class HelpdeskOfficerAdminForm(forms.ModelForm):
    class Meta:
        model = HelpdeskOfficer
        fields = (
            'name',
            'designation',
            'department',
            'phone',
            'email',
            'office_hours',
            'sort_order',
            'is_active',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'vTextField', 'size': 60}),
            'designation': forms.TextInput(attrs={'class': 'vTextField', 'size': 60}),
            'department': forms.TextInput(attrs={'class': 'vTextField', 'size': 60}),
            'phone': forms.TextInput(attrs={'class': 'vTextField', 'size': 30}),
            'email': forms.EmailInput(attrs={'class': 'vTextField', 'size': 60}),
            'office_hours': forms.TextInput(attrs={'class': 'vTextField', 'size': 60}),
            'sort_order': forms.NumberInput(attrs={'min': 0, 'style': 'width: 6rem;'}),
        }


class HelpdeskIssueAdminForm(forms.ModelForm):
    class Meta:
        model = HelpdeskIssue
        fields = (
            'name',
            'email',
            'mobile',
            'registration_no',
            'subject',
            'message',
            'status',
        )
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5, 'cols': 80}),
        }


class HelpdeskIssueForm(forms.ModelForm):
    class Meta:
        model = HelpdeskIssue
        fields = ('name', 'email', 'mobile', 'registration_no', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'portal-input',
                'placeholder': 'Your full name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'portal-input',
                'placeholder': 'your.email@example.com',
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'portal-input',
                'placeholder': '10-digit mobile number',
            }),
            'registration_no': forms.TextInput(attrs={
                'class': 'portal-input',
                'placeholder': 'Registration number (if applicable)',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'portal-input',
                'placeholder': 'Brief subject of your issue',
            }),
            'message': forms.Textarea(attrs={
                'class': 'portal-input',
                'rows': 5,
                'placeholder': 'Describe your issue or problem in detail…',
            }),
        }
        labels = {
            'name': 'Full name',
            'email': 'Email address',
            'mobile': 'Mobile number',
            'registration_no': 'Registration number',
            'subject': 'Subject',
            'message': 'Issue / problem details',
        }