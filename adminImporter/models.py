from django.db import models

# Create your models here.

class DatasetImporter(models.Model):
    source = models.OneToOneField('adminManager.AdminSource', related_name='importer', on_delete=models.PROTECT)
    import_params = models.JSONField(blank=True, null=True)
    last_imported = models.DateTimeField(null=True, blank=True)

