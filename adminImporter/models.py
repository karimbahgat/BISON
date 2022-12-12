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
            'encoding': {'type':'string', 'default':'utf8'},
            'levels': LEVELS_SCHEMA,
        }
    }

    source = models.ForeignKey('adminManager.AdminSource', related_name='importers', on_delete=models.PROTECT)
    import_params_old = models.JSONField(blank=True, null=True)
    import_params = JSONField(schema=IMPORT_PARAMS_SCHEMA,
                                blank=True, null=True)
    last_imported = models.DateTimeField(null=True, blank=True)

# class ImportJob(models.Model):
#     importer = models.OneToOneField('DatasetImporter', related_name='importer')
#     created = models.DateTimeField(autoadd_now=True)

# OR

# class ImportRunner(models.Model):
#     represents a process that imports data from one or more importers
#     stores its own progress and deletes itself after completing
#     can be used to display if a dataset is currently importing and its status
#     waits to run until next in line
#     BUT maybe in fact we just use the DatasetImporter class
#     and just add an import_status and import_details field to it.... 
