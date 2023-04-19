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
                "level": {'type':'string'}, # should be integer but weird styling
                "id_field": {'type':'string'},
                "id_delimiter": {'type':'string'},
                "id_index": {'type':'string'}, # should be integer but weird styling
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

    # MAYBE NEED TO ADD SOME OF THESE OPTIONAL ENTRIES TO IMPORT PARAMS?
    # MAYBE THIS IS THE SIMPLEST, KEEPING CURRENT STRUCTURE
    # BUT MAKING IMPORTER MORE SOURCE-LIKE
    # "iso_field":"ISO_CC",
    # "level":1,
    # "type_field":"ADMINTYPE",
    # "name_field":"NAME",
    # "dissolve":"ISO_SUB",
    # "drop_fields":["COLORMAP","LAND_RANK","LAND_TYPE","Shape_Area","Shape_Leng"],
    # "source_updated":"14 May 2021",
    # "source_url":"https://www.arcgis.com/home/item.html?id=9bc93fabc8d94747a22e811642ca426d",
    # "license":"ESRI License",
    # "license_detail":"See license url",
    # "license_url":"https://www.esri.com/en-us/legal/redistribution-rights"

    # OOOOR
    # MAYBE SWITCH SO ANY FILE THAT IS ITS OWN STANDALONE DATASET W SEPARATE URL ETC
    # HAS TO BE A SEPARATE SOURCE, WHERE MULTIPLE SOURCES CAN BE LINKED TO A SINGLE
    # SOURCEDISTRIBUTOR... 

    # OOOOR
    # MAYBE SWITCH SO SOURCES CAN BE NESTED, EACH WITH VARYING LEVEL OF DETAIL,
    # EG ALL DETAIL CAN BE AT TOP SOURCE LEVEL (EG GADM) OR AT BOTTOM (EG GEOBOUNDARIES AGO ADM1)
    # THIS IS TRACKED VIA .BELONGS_TO ATTR, WHICH IS DIFF FROM .BASED_ON...? 
    # AND IMPORTER IS OPTIONAL, EG:
    # NATEARTH - NATEARTH 501 - ADM0 FILE (W/IMPORTER)
    #                           ADM1 FILE (W/IMPORTER)
    # ESRI - ADM0 - DATE (W/IMPORTER)
    # GADM - GADM 4 - ISO ADM1 (W/IMPORTER)
    # GEOBOUNDARIES - GEOBOUNDARIES 5 - AGO ADM0 (W/IMPORTER)
    #                                   AGO ADM1 (W/IMPORTER)
    # OCHA COD - OCHA BURKINA FASO - ADM0 (W/IMPORTER)
    # UN SALB - SENEGAL - 2002-2010 (W/IMPORTER)
    # IPUMS - NIGERIA - ADM1 - 1976 (W/IMPORTER)
    # WOF - COUNTRY (W/IMPORTER)
    #     - REGION (W/IMPORTER)
    # OSM - ISO (W/IMPORTER)
    # CSHAPES - CSHAPES 2.0 (W/IMPORTER) [TIME DERIVED PER ROW]

