'''
Downloads zipfiles containing shapefiles for each country
and automatically generates the sourceMetaData.json file.

Does so using precollected csv file containing most of the necessary
metadata (TODO: ADD CREDIT). Output should be checked.

Countries for which shapefiles couldnt be automatically found:
MMR (link was for search results of relevant datasets)
    [but excluding anyway since "MIMU geospatial datasets cannot be used on online platform unless with prior written agreement from MIMU"]
GNB (zipfile was empty, had to instead download the gdb and convert to zipped shapefile)
ARE (file was a .rar file, so had to be manually downloaded+unzipped)
TJK (source_url was missing, but turns out spatial datasets exists on all of HDX)

Countries in the csv that were not related to OCHA and hence moved to the "Other" collection
'''


import urllib.request
from zipfile import ZipFile
import os
import io
import sys
import json
import warnings
import datetime
import csv
import re
from openpyxl import load_workbook

def main():
    from adminManager import models
    from adminImporter.models import DatasetImporter

    from django.db import transaction
    from django.utils import timezone

    from . import utils

    # read csv
    csv_path = os.path.join(os.path.dirname(__file__), 'ocha-meta.xlsx')
    print(csv_path)
    wb = load_workbook(filename=csv_path)
    table = wb.worksheets[0]
    exceldata = list(table.values)
    fields = list(exceldata[0])
    rows = []
    for _row in exceldata[1:]:
        row = dict(zip(fields, _row))
        rows.append(row)

    with transaction.atomic():

        # get top source
        root_source = models.AdminSource.objects.get(name='UN OCHA')

        # loop rows of csv
        for row in rows:
            # skip if the iso folder already exists
            iso = row['iso3']
            print('')
            print(iso)

            # those without org/src seem to be based on thirdparty data
            #if not row['src_org']:
            #    continue

            # get sources
            source_url = row['src_url']
            if not source_url:
                warnings.warn('iso {} has no source_url, skipping'.format(iso))
                continue
            sources = []
            if row['src_org']:
                sources.append(row['src_org'])
            if row['src_name']:
                sources.append(row['src_name'])

            # dates
            year = row['src_date'].year if row['src_date'] else None
            updated = row['src_update'].strftime('%Y-%m-%d') if row['src_update'] else None
            if not updated:
                warnings.warn('Missing update date for {}'.format(iso))
            if not year:
                warnings.warn('Missing year for {}'.format(iso))

            # license
            # license = 'Creative Commons Attribution for Intergovernmental Organisations'
            # license_url = source_url

            # create country source
            meta = {
                'parent': root_source,
                'name': row['name'],
                'url': source_url,
                'valid_from': f'{year}-01-01' if year else None,
                'valid_to': f'{year}-12-31' if year else None,
                #'sources': sources,
                #'updated': updated,
                'type': 'DataSource',
            }
            src = models.AdminSource(**meta)
            src.save()

            # TODO: add source lineage
            # ... 

            # determine import params by parsing the country download links
            try:
                resp = urllib.request.urlopen(source_url)
            except urllib.error.HTTPError:
                warnings.warn('Bad source url for {}: {}'.format(iso, source_url))
                continue
            raw = resp.read().decode('utf8')

            # hacky parse the html into elements
            elems = raw.replace('>','<').split('<')
            elems = (elem for elem in elems)
            
            # look for zipfile/shapefile links
            import_params_list = []
            root = 'https://data.humdata.org'
            for elem in elems:
                if elem.startswith('a href') and '.zip' in elem:
                    start = elem.find('"') + 1
                    end = elem.find('"', start)
                    link = root + elem[start:end]
                    zipname = link.split('/')[-1]
                    if '_admall_' in zipname.lower():
                        continue
                    if 'server' in zipname.lower():
                        continue
                    if '_emf.' in zipname.lower():
                        continue
                    if '.gdb' in zipname.lower() or '_gdb' in zipname.lower():
                        continue

                    # look for shapefiles in zipfile
                    print('fetching:', link)
                    try:
                        filenames = list(utils.inspect_zipfile_contents(link))
                    except Exception as err: # urllib.error.HTTPError:
                        warnings.warn('Error fetching: {} - {}'.format(link, err))
                        continue
                    shapefiles = [fil for fil in filenames if fil.endswith('.shp')]
                    if shapefiles:
                        print('found zipfile with shapefiles', zipname, shapefiles)

                        # add to input
                        for subfile in shapefiles:
                            print('file', subfile)
                            if '_admall_' in subfile.lower():
                                continue

                            # levels
                            subfile_file = subfile.split('/')[-1]
                            matches = re.findall('_adm(\d)', subfile_file)
                            if not matches:
                                matches = re.findall('_admin(\d)', subfile_file)
                            if not matches:
                                matches = re.findall('_(\d)[_.]', subfile_file)
                            if not matches:
                                warnings.warn(f'Unable to determine adm level from filename: {subfile}')
                                continue
                            level = matches[0]
                            print(f'ADM{level}')
                            level = int(level)
                            levels = [
                                {
                                    'level': 0,
                                    'id': iso,
                                    'name_field': None,
                                }
                            ]
                            for lvl in range(1, level+1):
                                levels.append({
                                    'level': lvl,
                                    'id_field': f'ADM{lvl}_PCODE',
                                    'name_field': f'ADM{lvl}_EN',
                                })
                            
                            # import params
                            entry = {
                                'path':link,
                                'path_zipped_file':subfile,
                                'levels':levels
                            }
                            print(entry)
                            import_params_list.append(entry)

                            # inspect fields
                            # import shapefile
                            # path = '{}/{}'.format(link, subfile)
                            # reader = shapefile.Reader(path)
                            # print('fields:',reader.fields)

            if not import_params_list:
                warnings.warn("Couldn't find any zipfiles with shapefiles for {}".format(iso))
            
            # create importers
            for import_params in import_params_list:
                importer = DatasetImporter(
                    source=src,
                    import_params=import_params,
                    import_status='Pending',
                    status_updated=timezone.now(),
                )
                importer.save()
                