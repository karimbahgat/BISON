
import os
import json
from urllib.request import urlopen

from . import utils

import urllib.request
from zipfile import ZipFile
import io

def iter_gadm_country_links():
    # access the gadm country download page
    root = 'https://gadm.org/download_country40.html' #'https://gadm.org/download_country.html'
    raw = urllib.request.urlopen(root).read().decode('utf8')

    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # get all isos from the download page
    print('making list of isos')
    isos = []
    while elem != None:
        if elem.startswith('option value="'):
            elem = elem.replace('option value="', '')
            iso = elem[:3]
            if len(iso)==3 and iso.isalpha():
                #print(iso)
                isos.append(iso)
        elem = next(elems, None)

    # loop isos and urls
    print('iterating:')
    for iso in isos:
        #print(iso)
        url = 'https://geodata.ucdavis.edu/gadm/gadm4.0/shp/gadm40_{}_shp.zip'.format(iso)
        yield iso, url

def iter_gadm_country_zip_shapefiles(url):
    for filename in utils.inspect_zipfile_contents(url):
        if filename.endswith('.shp'):
            level = filename.split('_')[2].split('.')[0]
            level = int(level)
            yield level, filename

def generate_import_params(file_path, iso, level):
    # add
    #iso = os.path.basename(zip_path).split('.')[0]
    # def getidfield(lvl, level):
    #     if lvl == level:
    #         return f"ID_{lvl}"
    #     elif lvl > 0:
    #         return f"NAME_{lvl}" # not perfect but id for parent admins is missing
    #     else:
    #         return None
    params = {
        "encoding": "utf8",
        "path": file_path,
        "levels": [
            {
                "level": lvl,
                "id_field": f"ID_{level}", #getidfield(lvl, level), 
                "id_delimiter": '.',
                "id_index": lvl,
                "name_field": "COUNTRY" if lvl == 0 else f'NAME_{lvl}',
            }
            for lvl in range(level+1)
        ]
    }
    return params

def main():
    '''Run this function via python manage.py shell to populate the db'''
    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():

        # get top source
        root_source = models.AdminSource.objects.get(name='GADM')

        # create version source
        meta = {
            'parent': root_source,
            'name': 'v4.0.4',
            'url': 'https://gadm.org/download_country40.html',
            'type': 'DataSource',
            #'updated': '2022-03-25',
        }
        vsource = models.AdminSource(**meta)
        vsource.save()

        # iterate github country zipfiles
        for iso,zip_url in iter_gadm_country_links():
            print('--------')
            print(iso, zip_url)

            # create source for that country
            meta = {
                'parent': vsource,
                'name': f'{iso}',
                'url': zip_url,
                'type': 'DataSource',
                #'updated': '2022-03-25',
            }
            print(meta)
            src = models.AdminSource(**meta)
            src.save()

            for level,filename in iter_gadm_country_zip_shapefiles(zip_url):
                print(level, filename)

                file_path = f'{zip_url}/{filename}'
                import_params = generate_import_params(file_path, iso, level)
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
from adminImporter.scripts.import_gadm404 import main
main()
 
'''
