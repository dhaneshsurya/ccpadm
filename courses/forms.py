from django import forms

from .models import ProgramCourseInstruction


class ProgramCourseInstructionForm(forms.ModelForm):
    class Meta:
        model = ProgramCourseInstruction
        fields = ('program', 'title', 'message', 'sort_order', 'is_active')
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Optional heading, e.g. Important — read before selecting courses',
                'size': 70,
            }),
            'message': forms.Textarea(attrs={
                'rows': 6,
                'cols': 80,
                'placeholder': 'Instructions shown to students when this program is selected on the admission form.',
            }),
        }
        help_texts = {
            'program': 'Choose the program name exactly as students select it on the admission form.',
            'message': 'Plain text. Line breaks are preserved. Shown above the course table.',
            'sort_order': 'Lower numbers appear first when multiple instructions exist for one program.',
        }

    def clean_message(self):
        message = (self.cleaned_data.get('message') or '').strip()
        if not message:
            raise forms.ValidationError('Instruction message cannot be empty.')
        return message