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

def iter_countries():
    path = os.path.join(os.path.dirname(__file__), 'countries_codes_and_coordinates.csv')
    with open(path) as fobj:
        reader = csv.DictReader(fobj)
        for row in reader:
            iso = row['Alpha-3 code'].replace('"','').replace("'",'').strip()
            yield iso

def parse_country(iso):
    '''Determine metadaata from country page
    also define import params by parsing the available country download links.
    '''
    source_url = f'https://data.humdata.org/dataset/cod-ab-{iso.lower()}'
    print('parsing',source_url)
    try:
        resp = urllib.request.urlopen(source_url)
    except urllib.error.HTTPError:
        warnings.warn('Bad source url')
        return
    raw = resp.read().decode('utf8')

    # hacky parse the html into elements
    elems = raw.replace('>','<').split('<')
    elems = (elem for elem in elems)
    
    parsed = {'download_links':[], 'url':source_url, 'iso':iso}
    label = value = None
    root = 'https://data.humdata.org'
    for elem in elems:
        # get metadata label
        if elem.startswith('th') and 'dataset-label' in elem:
            label = next(elems)
            print('label:',repr(label))
        
        # get metadata value
        if elem.startswith('td') and 'dataset-details' in elem:
            text_vals = []
            while not elem.startswith('/td'):
                elem = next(elems).replace('\n','').replace('\t','').strip()
                if elem != '' and not elem in ('p','br','br/') and not elem.startswith(('span','div','a ','/')):
                    text_vals.append(elem)
            value = ' '.join(text_vals)
            print('value:',repr(value))

        # add key-value pair to parsed results
        if label != None and value != None:
            parsed[label] = value
            label = value = None # reset

        # look for zipfile/shapefile links
        if elem.startswith('a href') and '.zip' in elem:
            start = elem.find('"') + 1
            end = elem.find('"', start)
            link = root + elem[start:end]
            if '_admall_' in link.lower():
                continue
            if 'server' in link.lower():
                continue
            if '_emf.' in link.lower():
                continue
            if '.gdb' in link.lower() or '_gdb' in link.lower():
                continue

            parsed['download_links'].append(link)

    return parsed

def main(host, root_source):
    #from adminManager import models
    #from adminImporter.models import DatasetImporter

    #from django.db import transaction
    #from django.utils import timezone
    from dateutil.parser import parse as parse_date

    import utils

    # loop countries
    for iso in iter_countries():
        print('')
        print(iso)

        # parse metadata++ from country page
        parsed = parse_country(iso)
        print(parsed)
        if not parsed:
            print('unable to open url, skipping')
            continue

        # check if has downloadable shapefiles and generate import params
        import_params_list = []
        for link in parsed['download_links']:
            # look for shapefiles in zipfiles
            print('fetching:', link)
            try:
                filenames = list(utils.inspect_zipfile_contents(link))
            except Exception as err: # urllib.error.HTTPError:
                warnings.warn('Error fetching: {} - {}'.format(link, err))
                continue

            # loop shapefiles
            shapefiles = [fil for fil in filenames if fil.endswith('.shp')]
            if shapefiles:
                zipname = link.split('/')[-1]
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

        # get from/to validity
        validity = parsed['Reference Period']
        if '-' in validity:
            valid_from,valid_to = validity.split('-')
        else:
            valid_from = valid_to = validity
        # convert to datetime
        try: 
            valid_from = parse_date(valid_from.strip()).date()
        except: 
            valid_from = None
        try: 
            valid_to = parse_date(valid_to.strip()).date()
        except: 
            valid_to = None
        if not valid_from or not valid_to:
            warnings.warn('Missing date validity for {}'.format(iso))

        # update
        updated = parsed['Updated']
        updated = parse_date(updated.strip())
        if not updated:
            warnings.warn('Missing update date for {}'.format(iso))

        # license
        # license = 'Creative Commons Attribution for Intergovernmental Organisations'
        # license_url = source_url

        # create country source
        name = parsed['Location']
        note = f'''Provider: {parsed["Contributor"]}
Source: {parsed["Source"]}

Methodology: 
{parsed["Methodology"]}

Comments: 
{parsed["Caveats / Comments"]}
'''
        meta = {
            'parent': root_source,
            'name': name,
            'url': parsed['url'],
            'valid_from': valid_from.isoformat(),
            'valid_to': valid_to.isoformat(),
            'note': note,
            #'sources': sources,
            #'updated': updated,
            'type': 'DataSource',
        }
        #src = models.AdminSource(**meta)
        #src.save()
        print('sending',meta)
        src = utils.post_datasource(host, meta)
        print('received',src)

        # TODO: add source lineage
        # sources = []
        # if parsed['provider']:
        #     sources.append(parsed['provider'])
        # if parsed['source']:
        #     sources.append(parsed['source'])
        
        # create importers
        # for import_params in import_params_list:
        #     importer = DatasetImporter(
        #         source=src,
        #         import_params=import_params,
        #         import_status='Pending',
        #         status_updated=timezone.now(),
        #     )
        #     importer.save()
        if import_params_list:
            importers = [{'source':src, 'import_params':import_params}
                        for import_params in import_params_list]
            utils.post_datasource_importers(host, importers)

if __name__ == '__main__':
    
    # set which site host and top source to import into
    # http://localhost:8000 or https://boundarylookup.wm.edu
    host = 'http://localhost:8000'
    root_source = 5603
    #host = 'https://boundarylookup.wm.edu'
    #root_source = fdssfs
    
    # run
    main(host, root_source)
