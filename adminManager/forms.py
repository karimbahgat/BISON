from django.forms import ModelForm, HiddenInput

from .models import AdminSource

class AdminSourceForm(ModelForm):
    class Meta:
        model = AdminSource
        fields = ['type','name','url',
                'valid_from','valid_to',
                'citation', 'note'
                ]
        widgets = {'type': HiddenInput()}

