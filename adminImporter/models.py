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
                "level": {'type':'string'}, # should be integer
                "id_field": {'type':'string'},
                "name_field": {'type':'string'}
            }
        }
    }
    IMPORT_PARAMS_SCHEMA = {
        'type': 'dict',
        'keys': {
            'path': {'type':'string'},
            'encoding': {'type':'string'}, #'default':'utf8'},
            'levels': LEVELS_SCHEMA,
        }
    }
    STATUS_CHOICES = [
        ('Pending','Pending'),
        ('Importing','Importing'),
        ('Imported','Imported'),
        ('Failed','Failed'),
    ]

    source = models.ForeignKey('adminManager.AdminSource', related_name='importers', on_delete=models.CASCADE)
    import_params_old = models.JSONField(blank=True, null=True)
    import_params = JSONField(schema=IMPORT_PARAMS_SCHEMA,
                                blank=True, null=True)
    import_status = models.CharField(max_length=100, choices=STATUS_CHOICES, default="Pending")
    import_details = models.TextField(blank=True, null=True)
    status_updated = models.DateTimeField(null=True, blank=True)

