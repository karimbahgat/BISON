from django.shortcuts import render, redirect
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models.functions import Upper

import os
import csv
import logging
import traceback
import threading

from .models import DatasetImporter
from adminManager import models

# Create your views here.

# def datasource_import_all(request):
#     '''Not meant for users, only for internal use to quickly load
#     large amounts of data'''
#     params = request.GET.dict()
#     print(params)
#     replace = params.pop('replace','false').lower()
#     if len(params):
#         sources = models.AdminSource.objects.filter(**params)
#     else:
#         sources = models.AdminSource.objects.all()
#     for src in sources:
#         if replace == 'false':
#             if src.admins.all().count() > 0:
#                 # don't reimport populated sources if replace is false
#                 continue
#         print('importing from', src)
#         try:
#             datasource_import(request, src.pk)
#         except Exception as err:
#             print('error importing source:', err)

def datasource_clear(request, pk):
    '''Delete all boundaries from a source'''
    source = models.AdminSource(pk=pk)

    # start db transaction
    with transaction.atomic():
        # drop all existing source data
        source.admins.all().delete()

        # reset all importers
        importers = list(source.importers.all())
        for importer in importers:
            importer.import_status = 'Pending'
            importer.import_details = ''
            importer.status_updated = timezone.now()
        DatasetImporter.objects.bulk_update(importers, ['import_status','import_details','status_updated'])

    return redirect('dataset', source.pk)

def datasource_import(request, pk):
    '''Import all DatasetImporters defined for a source'''
    thread = threading.Thread(target=_datasource_import, args=(pk,))
    thread.start()
    return redirect('dataset', pk)

def _datasource_import(pk):
    source = models.AdminSource(pk=pk)

    # loop all pending importers
    for importer in source.importers.filter(import_status='Pending'):
        # update status
        importer.import_status = 'Importing'
        importer.import_details = ''
        importer.status_updated = timezone.now()
        importer.save()

        # run the import
        try:
            run_importer(importer)
            importer.import_status = 'Imported'
            importer.import_details = ''
        except:
            msg = traceback.format_exc()
            print('ERROR:', msg)
            importer.import_status = 'Failed'
            importer.import_details = msg

        # update status
        importer.status_updated = timezone.now()
        importer.save()

@csrf_exempt
def run_importer(importer):
    '''Runs a specific Importer, this is done by a backend, not a user'''
    source = importer.source

    #if request.method == 'GET':
    #    dfafds #return render(request, 'source_import.html')

    #elif request.method == 'POST':

    import shapefile
    import tempfile

    # required post args:
    # - date
    # - name_field (str or list)
    # - iso or iso_field: shortcut to lookup name for level 0

    #print('POST', request.POST)

    # load import params
    params = importer.import_params.copy()
    print('params', params)

    # load country data
    # WARNING: globals vars is not very good
    global iso2_to_3, iso3_to_name, name_to_iso3
    iso2_to_3 = {}
    iso3_to_name = {}
    name_to_iso3 = {}
    filedir = os.path.dirname(__file__)
    with open(os.path.join(filedir, 'scripts/countries_codes_and_coordinates.csv'), encoding='utf8', newline='') as f:
        csvreader = csv.DictReader(f)
        for row in csvreader:
            name = row['Country'].strip().strip('"')
            iso2 = row['Alpha-2 code'].strip().strip('"')
            iso3 = row['Alpha-3 code'].strip().strip('"')
            iso2_to_3[iso2] = iso3
            iso3_to_name[iso3] = name
            name_to_iso3[name] = iso3

    # # load country
    # iso = request.POST.get('iso', '')
    # iso = iso2_to_3[iso] if len(iso)==2 else iso
    
    # stream any uploaded zipfile to disk (to avoid memory crash)
    # temps = []
    # for input_name,fobj in request.FILES.items():
    #     filename = fobj.name
    #     if not filename.endswith('.zip'):
    #         raise Exception('Uploaded file must end with .zip, not: {}'.format(filename))
    #     with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
    #         temps.append(temp)
    #         temppath = temp.name
    #         for chunk in fobj.chunks():
    #             temp.write(chunk)

    # parse date
    def parse_date(dateval):
        '''Can be a year, year-month, or year-month-day'''
        dateparts = dateval.split('-')
        if len(dateparts) == 1:
            yr = dateparts[0]
            start = '{}-01-01'.format(yr)
            end = '{}-12-31'.format(yr)
        elif len(dateparts) == 2:
            yr,mn = dateparts
            start = '{}-{}-01'.format(yr,mn)
            end = '{}-{}-31'.format(yr,mn)
        elif len(dateparts) == 3:
            start = end = dateval
        else:
            raise Exception('"{}" is not a valid date'.format(dateval))
        return start,end

    # TODO: i think maybe this should be from the source instead? 
    if False: #params['valid_from'] and params['valid_to']:
        start1,end1 = parse_date(str(params['valid_from']))
        start2,end2 = parse_date(str(params['valid_to']))
        start = min(start1,start2)
        end = max(end1, end2)
    else:
        start = end = None

    # get source
    # source_name = params['source'][0]
    # source = models.BoundarySource.objects.filter(name=source_name).first()
    # if not source:
    #     source_cite = request.POST.get('source_citation', '')
    #     source_note = request.POST.get('source_note', '')
    #     source_url = request.POST.get('source_url', '')
    #     source = models.BoundarySource(type="DataSource",
    #                                     name=source_name,
    #                                     citation=source_cite,
    #                                     note=source_note,
    #                                     url=source_url,
    #                                     )
    #     source.save()

    # run import
    _params = params
    _params['input_path'] = _params.pop('path') # rename path arg
    print('')
    print('-'*30)
    print('import args', _params)

    # open and parse data
    reader,data = parse_data(**_params)

    # add to db
    print('adding to db')
    common = {'source':source, 'start':start, 'end':end}
    with transaction.atomic():
        add_to_db(reader, common, data)

    #except Exception as err:
    #    error_count += 1
    #    logging.warning("error importing data for '{}': {}".format(_params['input_path'], traceback.format_exc()))
    #    continue

    # delete tempfiles
    # for temp in temps:
    #     os.remove(temp.name)

    # redirect
    #return redirect('source', source.pk)

def download_file(urlpath):
    from urllib.request import urlretrieve
    _,ext = os.path.splitext(urlpath)
    path,headers = urlretrieve(urlpath)
    os.rename(path, path+ext)
    return path+ext

def detect_shapefile_encoding(path):
    print('detecting encoding')
    encoding = None

    # look for cpg file
    if '.zip' in path:
        # inside zipfile
        from zipfile import ZipFile
        zippath,relpath = path.split('.zip')[:2]
        zippath += '.zip'
        with ZipFile(zippath) as archive:
            relpath = os.path.splitext(relpath)[0]
            relpath = relpath.lstrip('/\\')
            for ext in ['.cpg','.CPG']:
                try: 
                    with archive.open(relpath+ext) as cpg:
                        encoding = cpg.read().decode('utf8')
                    break
                except:
                    pass
    else:
        # normal path
        basepath = os.path.splitext(path)[0]
        for ext in ['.cpg','.CPG']:
                try: 
                    with archive.open(relpath+ext) as cpg:
                        encoding = cpg.read().decode('utf8')
                    break
                except:
                    pass
    
    # not sure about the format of expected names
    # so just check for some common ones
    if encoding:
        print('found',encoding)
        if '1252' in encoding:
            return 'latin1' # 1252 doesn't always work, maybe meant latin1 which is almost the same
            #return 'cp1252'

    # autotry diff encodings
    #encodings = ['utf8','latin']
    #for enc in encodings:
    #    try:
    #        # try read all records
    #        for r in reader.iterRecords():
    #            pass
    #        # read was successful, use this encoding
    #        return enc
    #    except UnicodeDecodeError:
    #        continue

def parse_data(**params):
    # read shapefile from temporary zipfile
    # (name_field is a list of one or more name_field inputs from a form)

    # download data if needed
    # path = params['input_path']
    # if path.startswith('http'):
    #     urlpath = path
    #     if '.zip' in urlpath:
    #         # only download the highest level zipfile
    #         urlpath,relpath = urlpath.split('.zip')[:2]
    #         urlpath += '.zip'
    #         path = download_file(urlpath)
    #         params['input_path'] = path + relpath
    #     elif urlpath.endswith('.shp'):
    #         for ext in ('.shp','.shx','.dbf'):
    #             path = download_file(urlpath.replace('.shp',ext))
    #             params['input_path'] = path
    #     else:
    #         raise Exception('External input data must be inside zipfile')

    # get shapefile encoding
    reader_opts = {}
    encoding = params.get('encoding', None)
    if encoding:
        # manually specified
        reader_opts['encoding'] = encoding
    else:
        # otherwise try to autodetect
        encoding = detect_shapefile_encoding(params['input_path'])
        if encoding:
            reader_opts['encoding'] = encoding
        
    # define nested shapefile groups reading
    def iter_shapefile_groups(reader, group_field=None, subset=None):
        if group_field:
            # return in groups
            def iterRecords():
                if subset:
                    # iterate only at subset indices
                    for i in subset:
                        rec = reader.record(i, fields=[group_field])
                        yield rec
                else:
                    # iterate all records
                    for rec in reader.iterRecords(fields=[group_field]):
                        yield rec
            # get all values of group_field with oid
            vals = ((rec[0],rec.oid) for rec in iterRecords())
            # group oids by group value
            import itertools
            key = lambda x: x[0]
            for groupval,items in itertools.groupby(sorted(vals, key=key), key=key):
                # yield each group value with list of index positions
                positions = [oid for _,oid in items]
                yield groupval, positions
        else:
            # return only a single group of entire shapefile
            groupval = ''
            positions = list(range(len(reader)))
            yield groupval, positions

    def iter_nested_shapefile_groups(reader, level_defs, level=0, subset=None):
        # iterate through each group, depth first
        # NOTE: level arg is only the index as we iterate through the entrise in the level_defs list
        # ...and does not necessarily correspond to the adm level (eg if only adm0 and adm2 is defined).
        # ...The adm level has to be explicitly defined by level_def['level'].
        data = []
        level_def = level_defs[level]
        group_field = level_def['id_field'] if int(level_def['level']) > 0 else level_def.get('id_field', None) # id not required for adm0
        fields = [v for k,v in level_def.items() if k.endswith('_field') and v != None]
        for groupval,_subset in iter_shapefile_groups(reader, group_field, subset):
            # override all level 0 with a single iso country lookup
            # WARNING: this assumes that id_field is iso code if is set for level0
            if level == 0 and groupval:
                try:
                    if len(groupval) == 2:
                        level_def['name'] = iso3_to_name[iso2_to_3[groupval]]
                    elif len(groupval) == 3:
                        level_def['name'] = iso3_to_name[groupval]
                    else:
                        continue
                except KeyError:
                    continue
            # item
            item = {'id':groupval, 'level':level_def['level'], 
                    'positions':_subset}
            rec = reader.record(_subset[0], fields=fields)
            item['name'] = level_def['name'] if level_def.get('name', None) else rec[level_def['name_field']]
            # next
            if level_def != level_defs[-1]:
                # recurse into next group_field
                children = iter_nested_shapefile_groups(reader, level_defs, level+1, _subset)
            else:
                # last group_field/max depth
                children = []
            data.append({'item':item,'children':children})
        return data

    # begin reading shapefile
    import shapefile
    reader = shapefile.Reader(params['input_path'], **reader_opts)
    print(reader)

    # parse nested structure
    print('parsing shapefile nested structure')
    data = iter_nested_shapefile_groups(reader, params['levels'])
    #print(data)

    return reader, data

def dissolve(geoms, dissolve_buffer=None):
    from shapely.geometry import shape
    from shapely.ops import cascaded_union
    dissolve_buffer = 1e-7 if dissolve_buffer is None else dissolve_buffer # default dissolve buffer is approx 1cm
    print('dissolving',len(geoms))
    # dissolve into one geometry
    if len(geoms) > 1:
        #print('loading shape')
        geoms = [shape(geom) for geom in geoms]
        #print('buffering')
        geoms = [geom.buffer(dissolve_buffer) for geom in geoms] # fill in gaps prior to merging to avoid nasty holes causing geometry invalidity
        #print('unioning')
        dissolved = cascaded_union(geoms)
        #print('finishing')
        dissolved = dissolved.buffer(-dissolve_buffer) # shrink back the buffer after gaps have been filled and merged
        # attempt to fix any remaining invalid result
        if not dissolved.is_valid:
            dissolved = dissolved.buffer(0)
        #print('geo interface')
        dissolved_geom = dissolved.__geo_interface__
    else:
        dissolved_geom = geoms[0]['geometry']
    
    return dissolved_geom

def add_to_db(reader, common, entries, parent=None):
    source = common['source']
    start = common['start']
    end = common['end']
    for entry in entries:
        #print(entry['item'])

        groupval = entry['item']['id']
        level = entry['item']['level']
        name = entry['item']['name']
        subset = entry['item']['positions']
        if not name:
            continue
        #name_obj,created = models.AdminName.objects.get_or_create(name__iexact=name.upper())
        try:
            name_obj = models.AdminName.objects.alias(name_upper=Upper('name')).get(name_upper=name.upper())
            #print('name found')
        except:
            name_obj = models.AdminName(name=name)
            name_obj.save()
            #print('name created')

        if entry['children']:
            print('parent node:', entry['item'])

            # create parent node
            ref = models.Admin(parent=parent, source=source, level=level)
            ref.save()
            ref.names.add(name_obj)

            # process all children one level deeper
            add_to_db(reader, common, entry['children'], parent=ref)

        else:
            # reached leaf node
            print('leaf node:', entry['item'])
            # get geometry, dissolve if multiple with same id
            assert len(subset) >= 1
            if len(subset) == 1:
                i = subset[0]
                shape = reader.shape(i)
                geom = shape.__geo_interface__
            elif len(subset) > 1:
                geoms = [reader.shape(i).__geo_interface__
                        for i in subset]
                geom = dissolve(geoms) #, dissolve_buffer)
            # create ref
            #print('saving')
            ref = models.Admin(parent=parent, source=source, level=level, 
                                geom=geom, valid_from=start, valid_to=end)
            ref.save()
            ref.names.add(name_obj)
