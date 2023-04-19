
import os
import json
import requests

from . import utils

def get_gb_meta(iso, level):
    url = f"https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/{iso}/ADM{level}/geoBoundaries-{iso}-ADM{level}.shp"
    meta = requests.get(url).json()
    return meta

def generate_import_params(iso, level):
    # add
    params = {
        "encoding": "utf8",
        "path": f"https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/{iso}/ADM{level}/geoBoundaries-{iso}-ADM{level}.shp",
        #"path": f"https://media.githubusercontent.com/media/wmgeolab/geoContrast/stable/{path}/gadm40_{iso}_{level}.shp",
        "levels": [
            {
                "level": 0,
                "id_field": 'shapeGroup', 
                "name_field": "shapeGroup",
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


if __name__ == '__main__':

    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():

        # common params
        source_params = {
            "type": "DataSource",
            "name": "geoBoundaries (Open)",
            "valid_from": None,
            "valid_to": None,
            "url": "https://www.geoboundaries.org/",
        }
        print(source_params)
        src = models.AdminSource(**source_params)
        src.save()

        # iterate github country zipfiles
        owner,repo = 'wmgeolab', 'geoBoundaries'
        for iso_path in utils.iter_git_folders(owner, repo, 'releaseData/gbOpen'):
            print('--------')
            print(iso_path)
            iso = os.path.basename(iso_path)

            # generate input params for each level path
            #for lvl_num in range(4+1):
            #    lvl = f'ADM{lvl_num}'
            for lvl_path in utils.iter_git_folders(owner, repo, iso_path):
                lvl = os.path.basename(lvl_path)

                meta = get_gb_meta(iso, lvl)
                yr = meta['boundaryYear']
                start = f'{yr}-01-01'
                end = f'{yr}-12-31'

                dfsdfs

                meta['boundarySource']
                meta['boundarySourceURL']

                source_params = get_source_params_from_meta(meta)

                import_params = generate_import_params(iso, int(lvl[-1]))
                print(import_params)
                import_params['input'].append(import_params)

