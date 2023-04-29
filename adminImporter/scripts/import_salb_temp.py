'''
Get from temporary storage of previous downloads, since the salb website is currently broken
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import re
import sys
import json
import logging
import datetime
import shapefile

# redirect to logfile
logger = sys.stdout #open('download_log.txt', mode='w', encoding='utf8', buffering=1)
#sys.stdout = logger
#sys.stderr = logger

# access the gadm country download page
root = 'https://www.unsalb.org'

def iter_countries():
    path = r'P:\Public Folder\Boundary Tracker Test Data\SALB'
    for iso in os.listdir(path):
        if iso.startswith('download'):
            continue
        yield iso

def iter_country_file_info(iso):
    path = r'P:\Public Folder\Boundary Tracker Test Data\SALB' + f'/{iso}'
    for fil in os.listdir(path):
        if fil.endswith('-sourceMetaData.json'):
            info_path = os.path.join(path, fil)
            info = json.loads(open(info_path).read())
            yield info
        
def main(host, root_source):
    #from adminManager import models
    #from adminImporter.models import DatasetImporter

    #from django.db import transaction
    #from django.utils import timezone

    import utils

    # loop countries
    print('begin')
    for iso in iter_countries():
        print('')
        print(iso)
        
        # create country source
        countrylink = f'{root}/en/data/{iso.lower()}'
        meta = {
            'parent': root_source,
            'name': f'{iso}',
            'url': countrylink,
            'type': 'DataSource',
        }
        print('sending',meta)
        #cosource = models.AdminSource(**meta)
        #cosource.save()
        cosource = utils.post_datasource(host, meta)
        print('received',cosource)

        # loop files
        for info in iter_country_file_info(iso):
            print('file info', info)

            # TODO: parse and create source lineage
            # ... 

            fromdate = datetime.date.fromisoformat(info['valid_from'])
            todate = datetime.date.fromisoformat(info['valid_to'])
            updated = info['source_updated']

            # create timeperiod source
            name = fromdate.isoformat() if fromdate else '?'
            name += ' to '
            name += todate.isoformat() if todate else '?'
            meta = {
                "parent":cosource,
                "name":name,
                "valid_from":fromdate.isoformat() if fromdate else None,
                "valid_to":todate.isoformat() if todate else None,
                #"source":["UN SALB"],
                #"updated":updated.isoformat(),
                #"url":countrylink,
                "type":"DataSource",
            }
            print('sending',meta)
            #src = models.AdminSource(**meta)
            #src.save()
            src = utils.post_datasource(host, meta)
            print('received',src)

            # determine path from first input
            # should be same for all importers
            input = info['input'][0]
            relpath = input['path']
            zipname = relpath.split('.zip')[0] + '.zip'
            shapefile_name = relpath.split('.zip/')[1]
            ziplink = f'https://filedn.com/lvxzpqbRuTkLnAjfFXe7FFu/Boundary%20Tracker%20Test%20Data/SALB/{iso}/{zipname}'

            # create separate importers by dissolving each level
            # most salb files are ADM2 indicated by ADM1NM and ADM2NM fields
            # in rare cases, ADM2NM will be empty, indicating an adm1 boundary
            importers = []
            max_level = 2
            for level in range(max_level+1):
                # create importer
                import_params = {
                    'path':ziplink,
                    #'path_ext':'.zip',
                    'path_zipped_file':shapefile_name,
                    #'encoding':'utf8',
                    'levels':[
                        {'level':_lev,
                        'id': iso if _lev == 0 else '',
                        'id_field':'ADM{}CD'.format(_lev) if _lev > 0 else '',
                        'name_field':'ADM{}NM'.format(_lev) if _lev > 0 else None,
                        #'codes':[{'type':'ISO 3166-1 alpha-3', 'value':iso if _lev==0 else None}]
                        }
                        for _lev in range(level+1)
                    ]
                }
                #import_params['levels'][0]['id'] = iso # set adm0 id to country iso
                print('sending',import_params)

                # importer = DatasetImporter(
                #     source=src,
                #     import_params=import_params,
                #     import_status='Pending',
                #     status_updated=timezone.now(),
                # )
                # importer.save()
                meta = dict(
                    source=src,
                    import_params=import_params,
                )
                importers.append(meta)
            
            # submit importers to api
            utils.post_datasource_importers(host, importers)

if __name__ == '__main__':

    # set which site host and top source to import into
    # http://localhost:8000 or https://boundarylookup.wm.edu
    #host = 'http://localhost:8000'
    #root_source = 5575
    host = 'https://boundarylookup.wm.edu'
    root_source = 5402
    
    # run
    main(host, root_source)
