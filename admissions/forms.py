from django_ckeditor_5.widgets import CKEditor5Widget
from django import forms

from accounts.rich_text import clean_rich_text

from .models import AdmissionSubmitInstruction


class AdmissionSubmitInstructionForm(forms.ModelForm):
    class Meta:
        model = AdmissionSubmitInstruction
        fields = ('heading', 'notice', 'sort_order', 'is_active')
        widgets = {
            'heading': forms.TextInput(attrs={
                'placeholder': 'e.g. Important — read before submitting',
                'size': 70,
            }),
            'notice': CKEditor5Widget(config_name='full'),
        }
        help_texts = {
            'heading': 'Displayed as the popup title when students submit their application.',
            'notice': 'Rich text with full formatting. Shown in the submit confirmation popup.',
            'sort_order': 'Lower numbers appear first if multiple active instructions exist.',
        }

    def clean_heading(self):
        heading = (self.cleaned_data.get('heading') or '').strip()
        if not heading:
            raise forms.ValidationError('Heading cannot be empty.')
        return heading

    def clean_notice(self):
        return clean_rich_text(self.cleaned_data.get('notice'), field_label='Notice content')