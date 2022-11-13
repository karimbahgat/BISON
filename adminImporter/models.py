from django.db import models
from django_jsonform.models.fields import JSONField

# Create your models here.

class DatasetImporter(models.Model):
    LEVELS_SCHEMA = {
        'type': 'array',
        'minItems': 1,
        'items': {
            'type': 'dict',
            'keys': {
                "level": {'type':'int'},
                "id_field": {'type':'str'},
                "name_field": {'type':'str'}
            }
        }
    }
    INPUT_SCHEMA = {
        'type': 'array',
        'minItems': 1,
        'items': {
            'type': 'dict',
            'keys': {
                'path': {'type':'str'},
                'levels': LEVELS_SCHEMA,
            }
        }
    }
    IMPORT_PARAMS_SCHEMA = {
        'type': 'dict',
        'keys': {
            'input': INPUT_SCHEMA,
        }
    }

    source = models.OneToOneField('adminManager.AdminSource', related_name='importer', on_delete=models.PROTECT)
    import_params_old = models.JSONField(blank=True, null=True)
    import_params = JSONField(schema=IMPORT_PARAMS_SCHEMA,
                                blank=True, null=True)
    last_imported = models.DateTimeField(null=True, blank=True)

