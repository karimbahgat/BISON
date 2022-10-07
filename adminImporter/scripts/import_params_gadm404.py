
import os
import json

import utils

def generate_input_params(zip_path, level):
    # add
    iso = os.path.basename(zip_path).split('.')[0]
    def getidfield(lvl, level):
        if lvl == level:
            return f"ID_{lvl}"
        elif lvl > 0:
            return f"NAME_{lvl}" # not perfect but id for parent admins is missing
        else:
            return None
    input = {
        "encoding": "utf8",
        "path": f"https://media.githubusercontent.com/media/wmgeolab/geoContrast/stable/{path}/gadm40_{iso}_{level}.shp",
        "levels": [
            {
                "level": lvl,
                "id_field": getidfield(lvl, level), 
                "name_field": "COUNTRY" if lvl == 0 else f'NAME_{lvl}',
            }
            for lvl in range(level+1)
        ]
    }
    return input


if __name__ == '__main__':

    # common params
    import_params = {
        "input": [],
        "valid_from": None,
        "valid_to": None,
        "source": [
            "GADM v4.0.4"
        ]
    }

    # iterate github country zipfiles
    for path in utils.iter_git_folders('wmgeolab', 'geoContrast', 'sourceData/GADM/countryfiles'):
        print('--------')
        print(path)

        # generate input params for that path
        for lvl in range(5+1):
            input_params = generate_input_params(path, lvl)
            #print(input_params)
            import_params['input'].append(input_params)

    with open('adminImporter/scripts/gadm404.json', 'w') as fobj:
        fobj.write(json.dumps(import_params))
