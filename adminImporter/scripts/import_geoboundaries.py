
import os
import json
from urllib.request import urlopen

from . import utils

import urllib.request
from zipfile import ZipFile
import io
from csv import DictReader

def iter_country_level_rows():
    # access the geoboundary (open) csv file
    root = 'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/v5.0.0'
    csv_path = 'releaseData/geoBoundariesOpen-meta.csv'
    url = f'{root}/{csv_path}'
    raw = [l.decode('utf8') for l in urllib.request.urlopen(url).readlines()]
    reader = DictReader(raw, delimiter=',', quotechar='"')

    for row in reader:
        iso = row['boundaryISO']
        level = int(row['boundaryType'][-1])
        url = f'https://github.com/wmgeolab/geoBoundaries/raw/v5.0.0/releaseData/gbOpen/{iso}/ADM{level}/geoBoundaries-{iso}-ADM{level}.shp'
        yield iso,level,url,row

def generate_import_params(file_path, iso, level):
    # add
    params = {
        "encoding": "utf8",
        "path": file_path,
        "levels": [
            {
                "level": 0,
                "id_field": 'shapeGroup', 
                "name_field": "shapeName",
            }
        ]
    }
    if level > 0:
        params['levels'].append(
            {
                "level": level,
                "id_field": 'shapeID', 
                "name_field": 'shapeName',
            }
        )
    return params

def main():
    '''Run this function via python manage.py shell to populate the db'''
    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():

        # get top source
        root_source = models.AdminSource.objects.get(name='geoBoundaries')

        # create version source
        meta = {
            'parent': root_source,
            'name': 'v5.0.0',
            'url': 'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/v5.0.0',
            'type': 'DataSource',
            #'updated': '2022-12-19',
        }
        vsource = models.AdminSource(**meta)
        vsource.save()

        # iterate github country zipfiles
        key = lambda x: x[:2]
        for iso,level,url,row in sorted(iter_country_level_rows(), key=key):
            print('--------')
            print(iso, level, url)

            # TOTO: fetch and create derived sources...
            # ie from boundarySource and boundarySourceUrl
            # ... 

            # create source for that country
            yr = row['boundaryYearRepresented']
            if len(yr) != 4:
                # TODO: hardcoded for the only known example Bahamas ADM1
                print('ERROR: unknown year', yr)
                yr = None
            start = f'{yr}-01-01' if yr else None
            end = f'{yr}-12-31' if yr else None
            meta = {
                'parent': vsource,
                'name': f'{row["boundaryName"]} ADM{level}',
                'url': url,
                'valid_from': start,
                'valid_to': end,
                'type': 'DataSource',
                #'updated': '2022-12-19',
            }
            print(meta)
            src = models.AdminSource(**meta)
            src.save()

            # create importer
            import_params = generate_import_params(url, iso, level)
            import_params['encoding'] = meta.get('encoding', 'utf8')
            print(import_params)

            importer = DatasetImporter(
                source=src,
                import_params=import_params,
                import_status='Pending',
                status_updated=timezone.now(),
            )
            importer.save()


'''
python manage.py shell
from adminImporter.scripts.import_geoboundaries import main
main()
 
'''
