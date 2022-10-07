
import os
import json

import utils

def generate_input_params(iso, level):
    # add
    input = {
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
        input['levels'].append(
            {
                "level": level,
                "id_field": 'shapeID', 
                "name_field": 'shapeName',
            }
        )
    return input


if __name__ == '__main__':

    # common params
    import_params = {
        "input": [],
        "valid_from": None,
        "valid_to": None,
        "source": [
            "geoBoundaries (Open)"
        ]
    }

    # iterate github country zipfiles
    owner,repo = 'wmgeolab', 'geoBoundaries', 
    for iso_path in utils.iter_git_folders(owner, repo, 'releaseData/gbOpen'):
        print('--------')
        print(iso_path)
        iso = os.path.basename(iso_path)

        # generate input params for each level path
        #for lvl_path in utils.iter_git_folders(owner, repo, iso_path):
        #    lvl = os.path.basename(lvl_path)
        for lvl_num in range(4+1):
            lvl = f'ADM{lvl_num}'

            input_params = generate_input_params(iso, int(lvl[-1]))
            #print(input_params)
            import_params['input'].append(input_params)

    with open('adminImporter/scripts/geoboundaries.json', 'w') as fobj:
        fobj.write(json.dumps(import_params))
