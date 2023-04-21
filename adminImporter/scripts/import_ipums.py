'''
Downloads the latest available shapefiles/zipfiles for each country
and automatically generates the sourceMetaData.json file.
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import re
import sys
import json
import warnings
import datetime
import itertools

# access the country download page
root_url = 'https://international.ipums.org'

def iter_country_downloads(raw):
    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    elem = next(elems)

    # get all country links
    for elem in elems:
        #print(elem)
        if elem == 'tr':
            # first cell = country name
            next(elems) # first skip weird newline
            next(elems) # td
            country = next(elems)
            next(elems) # /td
            # second cell = type
            next(elems) # first skip weird newline
            next(elems) # td
            typ = next(elems)
            next(elems) # /td
        if elem.startswith('a href') and '.zip' in elem:
            # download links
            link = root_url + elem.replace('a href=', '').strip('"')
            filename = link.split('/')[-1]
            match = re.search(r'[0-9]{4}', filename)
            if match:
                year = int(match.group(0))
            else:
                raise Exception("Couldn't find year in {}".format(filename))
            iso = filename.split('_')[1][:2].upper() # 2 digit iso
            print('-->', country, iso, year, typ, link)
            assert all([iso, year, link])
            yield country, iso, year, typ, link
            #country = iso = year = link = None

def main():
    '''Run this function via python manage.py shell to populate the db'''
    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():

        # get root source
        root = models.AdminSource.objects.get(name='IPUMS')

        # loop pages and download+unzip each
        #start = 0 # starts at item 0
        for level in [1,2,3]:
            subpage = {1: 'international/gis_yrspecific_1st.shtml',
                    2: 'international/gis_yrspecific_2nd.shtml',
                    3: 'international/gis_yrspecific_3rd.shtml'}[level]
            url = '{}/{}'.format(root_url, subpage)
            print('')
            print('looping country links from page', url)
            resp = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}))

            # get country links
            raw = resp.read().decode('utf8')
            countrylinks = list(iter_country_downloads(raw))

            # create level source
            meta = {
                'parent': root, 
                'name': f'ADM{level}',
                'url': url,
                'type': 'DataSource',
            }
            lvlsource = models.AdminSource(**meta)
            lvlsource.save()

            # loop each country iso
            key = lambda x: x[1]
            countrylinks = itertools.groupby(sorted(countrylinks, key=key), key=key)
            for iso,group in countrylinks:
                group = list(group)

                # make sure 2-digit filename country code equals iso2
                # true for all except the united kingdom
                if iso == 'UK':
                    iso = 'GB'

                # create country source
                meta = {
                    'parent': lvlsource, 
                    'name': f'{iso}',
                    'type': 'DataSource',
                }
                cosource = models.AdminSource(**meta)
                cosource.save()

                # loop each download year for country
                for country, iso, year, typ, link in group:
                    print('processing', country, iso, year, typ, link)
                    
                    # download file
                    # filename = link.split('/')[-1]
                    # if DOWNLOAD:
                    #     try:
                    #         urllib.request.urlretrieve(link, '{}/{}'.format(dst, filename))
                    #     except Exception as err:
                    #         warnings.warn("Couldn't download file {}-{}-{}: {}".format(iso, level, year, err))
                    #         continue
                    # if not os.path.exists(os.path.join(dst, filename)):
                    #     warnings.warn("Couldn't find file, skipping: {}".format(filename))
                    #     continue

                    # get update date and shapefile input path
                    updated = None
                    # archive = ZipFile('{}/{}'.format(dst, filename))
                    # for fil in archive.namelist():
                    #     if fil.endswith('.xml'):
                    #         raw = archive.open(fil).read().decode('utf8')
                    #         try:
                    #             updated = raw.split('<ModDate>')[1][:8]
                    #             yr,mn,dy = updated[:4], updated[4:6], updated[6:8]
                    #             updated = '{}-{}-{}'.format(yr,mn,dy)
                    #         except Exception as err:
                    #             warnings.warn("Couldn't find source update date for {}-{}: {}".format(iso, level, err))

                    # get shapefile input path
                    # shapefiles = [fil for fil in archive.namelist() if fil.endswith('.shp')]
                    # if len(shapefiles) > 1:
                    #     warnings.warn('Found {} shapefiles for {}-{}'.format(len(shapefiles), iso, level))
                    # shapefile_path = '{}/{}'.format(filename, shapefiles[0])

                    # create year source
                    meta = {
                        "parent":cosource,
                        "name":year,
                        "valid_from":f"{year}-01-01",
                        "valid_to":f"{year}-12-31",
                        #"source":["IPUMS"],
                        #"updated":updated,
                        "url":link,
                        "type": 'DataSource',
                    }
                    print(meta)
                    src = models.AdminSource(**meta)
                    src.save()

                    # create importer
                    import_params = {
                        'path':link,
                        'levels':[
                            {'level':0,
                            'id':iso,
                            #'id_field':'CNTRY_CODE',
                            'name_field':'CNTRY_NAME',
                            #'codes':[{'type':'ISO 3166-1 alpha-2', 'value':iso}],
                            },
                            {'level':level,
                            'id_field':'IPUM{}'.format(year),
                            'name_field':'ADMIN_NAME',
                            #'codes':[],
                            }
                        ]
                    }
                    importer = DatasetImporter(
                        source=src,
                        import_params=import_params,
                        import_status='Pending',
                        status_updated=timezone.now(),
                    )
                    importer.save()

