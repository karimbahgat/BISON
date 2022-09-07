from django.forms import ModelForm, HiddenInput

from .models import AdminSource

class AdminSourceForm(ModelForm):
    class Meta:
        model = AdminSource
        exclude = []
        widgets = {'type': HiddenInput()}

