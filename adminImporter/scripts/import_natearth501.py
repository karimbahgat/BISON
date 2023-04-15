
import os
import json
from urllib.request import urlopen

from . import utils

def get_adm0():
    # add
    params = {
        "encoding": "latin",
        "path": f"https://github.com/wmgeolab/geoContrast/raw/stable/sourceData/Natural_Earth/ne_10m_admin_x_prepped.zip/ne_10m_admin_0_countries.shp",
        "levels": [
            {
                "level": 0,
                "id_field": "ISO_A3", 
                "name_field": "NAME_LONG",
            }
        ]
    }
    return params


def get_adm1():
    # add
    params = {
        "encoding": "latin",
        "path": f"https://github.com/wmgeolab/geoContrast/raw/stable/sourceData/Natural_Earth/ne_10m_admin_x_prepped.zip/ne_10m_admin_1_states_provinces.shp",
        "levels": [
            {
                "level": 0,
                "id_field": "iso_a2", 
                "name_field": "admin",
            },
            {
                "level": 1,
                "id_field": "adm1_code", 
                "name_field": "name",
            }
        ]
    }
    return params


def get_adm2():
    params = {
        "encoding": "latin",
        "path": f"https://github.com/wmgeolab/geoContrast/raw/stable/sourceData/Natural_Earth/ne_10m_admin_x_prepped.zip/ne_10m_admin_2_counties.shp",
        "levels": [
            {
                "level": 0,
                "id_field": "ISO_A2", 
                "name_field": "ADMIN",
            },
            {
                "level": 2,
                "id_field": "ADM2_CODE", 
                "name_field": "NAME",
            }
        ]
    }
    return params


def main():
    '''Run this function via python manage.py shell to populate the db'''
    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    # get geocontrast source meta
    meta_url = 'https://github.com/wmgeolab/geoContrast/raw/stable/sourceData/Natural_Earth/sourceMetaData.json'
    meta = utils.get_metadata(meta_url)

    with transaction.atomic():

        # create source
        source_params = utils.get_source_params_from_meta(meta)
        source_params['url'] = 'https://www.naturalearthdata.com/downloads/10m-cultural-vectors'
        source_params['note'] = '''Multiple source urls: 
        https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries
        https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces
        https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-2-counties
        '''
        print(source_params)
        src = models.AdminSource(**source_params)
        src.save()

        # generate file importers
        funcs = [get_adm0, get_adm1, get_adm2]
        for func in funcs:
            import_params = func()
            print(import_params)
            
            importer = DatasetImporter(
                source=src,
                import_params=import_params,
                import_status='Pending',
                status_updated=timezone.now(),
            )
            importer.save()

