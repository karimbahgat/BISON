from django.forms import ModelForm, HiddenInput

from .models import DatasetImporter

class DatasetImporterForm(ModelForm):
    class Meta:
        model = DatasetImporter
        exclude = ['last_imported']
        widgets = {
            'source': HiddenInput()
        }

