
import os
import json
from urllib.request import urlopen

from . import utils

def generate_import_params(zip_path, level):
    # add
    iso = os.path.basename(zip_path).split('.')[0]
    # def getidfield(lvl, level):
    #     if lvl == level:
    #         return f"ID_{lvl}"
    #     elif lvl > 0:
    #         return f"NAME_{lvl}" # not perfect but id for parent admins is missing
    #     else:
    #         return None
    params = {
        "encoding": "utf8",
        "path": f"https://media.githubusercontent.com/media/wmgeolab/geoContrast/stable/{zip_path}/gadm40_{iso}_{level}.shp",
        "levels": [
            {
                "level": lvl,
                "id_field": f"ID_{lvl}", #getidfield(lvl, level), 
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

    # get geocontrast source meta
    meta_url = 'https://github.com/wmgeolab/geoContrast/raw/stable/sourceData/GADM/sourceMetaData.json'
    meta = utils.get_metadata(meta_url)

    with transaction.atomic():

        # create source
        source_params = utils.get_source_params_from_meta(meta)
        print(source_params)
        src = models.AdminSource(**source_params)
        src.save()

        # iterate github country zipfiles
        for path in utils.iter_git_folders('wmgeolab', 'geoContrast', 'sourceData/GADM/countryfiles'):
            print('--------')
            print(path)

            # generate file importers for that country
            for lvl in range(5+1):
                import_params = generate_import_params(path, lvl)
                import_params['encoding'] = meta.get('encoding', 'utf8')
                print(import_params)
                
                importer = DatasetImporter(
                    source=src,
                    import_params=import_params,
                    import_status='Pending',
                    status_updated=timezone.now(),
                )
                importer.save()

