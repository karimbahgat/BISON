from django.forms import ModelForm, HiddenInput

from .models import AdminSource

class AdminSourceForm(ModelForm):
    class Meta:
        model = AdminSource
        fields = ['parent','type','name','url',
                'valid_from','valid_to',
                'description', 'note'
                ]
        widgets = {'type': HiddenInput(), 'parent':HiddenInput()}

