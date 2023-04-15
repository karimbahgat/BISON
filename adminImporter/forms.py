from django.forms import ModelForm, HiddenInput

from .models import DatasetImporter

class DatasetImporterForm(ModelForm):
    class Meta:
        model = DatasetImporter
        exclude = ['import_status', 'status_updated']
        widgets = {
            'source': HiddenInput()
        }

