from typing import OrderedDict
from django.shortcuts import render, redirect
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models.functions import Upper
from django.db.models import Max
from django.core.exceptions import ObjectDoesNotExist
from django.forms import modelformset_factory

from background_task import background

import os
import csv
import logging
import traceback
import threading
import itertools

from adminManager.geometry import WKBGeometry

from .models import DatasetImporter
from .forms import DatasetImporterForm
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

def tasks_process(request):
    os.system("python manage.py process_tasks")

def tasks_clear(request):
    from background_task.models import Task
    tasks = Task.objects.all()
    # TODO: maybe don't delete if the pid indicated in .locked_by is still running
    print(f'deleting all {tasks.count()} tasks')
    tasks.delete()

def datasource_importers_edit(request, pk):
    '''Edit the importers of a data source'''
    src = models.AdminSource.objects.get(pk=pk)
    initial = {'source':src}

    if request.method == 'GET':
        # create editable import forms
        DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                    form=DatasetImporterForm,
                                                    extra=10, can_delete=True)
        queryset = src.importers.all()
        importer_forms = DatasetImporterFormset(queryset=queryset, 
                                                initial=[initial]*10) # one for each 'extra' form
        context = {'src':src, 'importer_forms': importer_forms}
        return render(request, 'adminImporter/source_importers_edit.html', context)


    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)

            # save importers
            DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                        form=DatasetImporterForm,
                                                        extra=0, can_delete=True)
            importer_forms = DatasetImporterFormset(data)
            for import_form in importer_forms:
                if import_form.is_valid():
                    if import_form.has_changed():
                        #print(import_form.cleaned_data)
                        # check for deletion
                        if import_form.cleaned_data['DELETE']:
                            import_form.instance.delete()
                            continue
                        # validate import params
                        import_params = import_form.cleaned_data['import_params']
                        if import_params['path']:
                            # probably should validate some more... 
                            import_form.save()
                else:
                    # not sure how to deal with invalid forms yet....
                    raise Exception(f'invalid form: {import_form.errors}')
                        
                #if importer_forms.is_valid():
                #    importer_forms.save()
                #else:
                #    print(importer_forms.errors)
                #    raise Exception('Need better input form error handling...')
                #    return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

                return redirect('dataset', src.pk)

            else:
                context = {'src':src, 'importer_forms':importer_forms}
                return render(request, 'adminManager/source_importers_edit.html', context)

def datasource_clear(request, pk):
    '''Delete all boundaries from a source'''
    source = models.AdminSource(pk=pk)

    # start db transaction
    with transaction.atomic():
        # drop all existing source data
        source.admins.all().delete()

        # reset all importers
        importers = list(source.all_imports().exclude(import_status='Pending'))
        for importer in importers:
            importer.import_status = 'Pending'
            importer.import_details = ''
            importer.status_updated = timezone.now()
        DatasetImporter.objects.bulk_update(importers, ['import_status','import_details','status_updated'])

    return redirect('dataset', source.pk)

def datasource_import(request, pk):
    '''For a given source, add all pending DatasetImporters to work queue.'''
    source = models.AdminSource(pk=pk)

    # get all pending importers
    importers = source.all_imports().filter(import_status='Pending')

    # add importers to work queue (although can be slow when running many tasks)
    with transaction.atomic():
        for importer in importers:
            run_importer(importer.pk)

    # manually create each Task and bulk add
    # from background_task.models import Task
    # task_objs = [create_import_task(importer) for importer in importers]
    # Task.objects.bulk_create(task_objs)

    # return immediately
    return redirect('dataset', pk)

# def create_import_task(importer):
#     '''Creates an import background task, but doesn't save it.'''
#     # WARNING: apparently there's more to it than saving task to db
#     # reverse engineered from source code, not sure that it works

#     # create task without saving
#     from background_task.models import TaskManager
#     func = run_importer
#     name = '%s.%s' % (func.__module__, func.__name__)
#     args = (importer.pk,)
#     kwargs = {}
#     priority = 0
#     queue = None
#     creator = None
#     task = TaskManager().new_task(
#         task_name=name,
#         args=args,
#         kwargs=kwargs,
#         priority=priority,
#         queue=queue,
#         creator=creator,
#     )
#     task.locked_by = '' # this is done in Task.save

#     # add task proxy to the background_task task list
#     from background_task.tasks import tasks
#     from background_task import signals
#     schedule = 0
#     proxy = tasks._task_proxy_class(name, func, schedule, queue,
#                                     remove_existing_tasks=False, runner=tasks._runner)
#     tasks._tasks[name] = proxy
#     signals.task_created.send(sender='create_import_task', task=task)

#     return task

@background(schedule=0) # adds this function to a work queue rather than run it
def run_importer(pk):
    '''Runs a specified importer, updating import status accordingly.'''
    # exit early if importer is not pending for some reason
    # (eg another worker got to it first)
    importer = DatasetImporter.objects.get(pk=pk)
    if importer.import_status != 'Pending':
        return

    # update status
    importer.import_status = 'Importing'
    importer.import_details = ''
    importer.status_updated = timezone.now()
    importer.save()

    # run the import
    try:
        _run_importer(importer)
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

def _run_importer(importer):
    '''Performs the actual work of importing data based on information from importer.'''
    source = importer.source
    print('')
    print('-'*30)
    print(f'started {importer}')

    #if request.method == 'GET':
    #    dfafds #return render(request, 'source_import.html')

    #elif request.method == 'POST':

    import shapefile
    import tempfile
    temps = []

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
    # for input_name,fobj in request.FILES.items():
    #     filename = fobj.name
    #     if not filename.endswith('.zip'):
    #         raise Exception('Uploaded file must end with .zip, not: {}'.format(filename))
    #     with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
    #         temps.append(temp)
    #         temppath = temp.name
    #         for chunk in fobj.chunks():
    #             temp.write(chunk)

    # download data if needed
    path = params['path']
    if path.startswith('http'):
        urlpath = path
        if '.zip' in urlpath or params.get('path_ext', '') == '.zip':
            # relative paths inside zipfiles are no longer supported
            # instead give a distinct zip 'path' along with 'path_zipped_file'
            # and override with path_ext if provided (eg dynamic urls that dont use filenames)
            loc_path = download_file(urlpath, params.get('path_ext'))
            params['path'] = loc_path
        elif urlpath.endswith('.shp'):
            for ext in ('.shp','.shx','.dbf'):
                loc_path = download_file(urlpath.replace('.shp',ext))
                if ext == '.shp':
                    params['path'] = loc_path
        else:
            raise Exception(f'External input data must be of type .zip or .shp, not {urlpath}')
    else:
        raise Exception(f'Only http based file paths are supported for now, not {path}')

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

    # get time period
    # i think maybe this should be from the source instead? 
    start = end = None
    if False: 
        # determine from start_field, end_field
        pass
        
    else:
        # determine time period from source
        if source.valid_from:
            start = parse_date(str(source.valid_from))[0]
        if source.valid_to:
            end = parse_date(str(source.valid_to))[-1]

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
    print('import args', _params)

    # open and parse data
    reader,data = parse_data(**_params)

    # add to db
    print('adding to db')
    common = {'source':source, 'start':start, 'end':end}
    print(common)
    with transaction.atomic():
        add_to_db(reader, common, data)

    print(f'finished {repr(importer)}')

    #except Exception as err:
    #    error_count += 1
    #    logging.warning("error importing data for '{}': {}".format(_params['path'], traceback.format_exc()))
    #    continue

    # delete tempfiles
    # print('cleanup')
    # for temp in temps:
    #     os.remove(temp.name)

    # redirect
    #return redirect('source', source.pk)

DL_CACHE_PREFIX = 'boundary_cache_'
DL_CACHE_MAX_FILES = 20
DL_TIMEOUT = 10  # in minutes

def get_dl_cache():
    '''Search tempdir for all files starting with DL_CACHE_PREFIX.
    Return a cache lookup with filename, and full file path.
    '''
    import tempfile
    tempdir = tempfile.gettempdir()
    files = [fil for fil in os.listdir(tempdir)
             if fil.startswith(DL_CACHE_PREFIX)]
    cache = {fil: os.path.join(tempdir, fil)
             for fil in files}
    return cache

# def calc_cache_size(cache):
#     size = 0
#     for path in cache.values():
#         size += os.path.getsize(path)
#     return size
    
def oldest_to_newest_file_paths(paths):
    key = lambda p: os.path.getmtime(p) # last modified timestamp
    paths = sorted(paths, key=key)
    return paths

def generate_url_hash(urlpath):
    '''Generate a unique hash for a given url.
    Ignores extension so that files with different extensions get same hashname.
    Returns urlhash,extension
    '''
    import hashlib
    urlpath_base,ext = os.path.splitext(urlpath)
    urlhash = hashlib.md5(urlpath_base.encode('utf8')).hexdigest()
    return urlhash,ext

def download_file(urlpath, file_ext=None):
    # determine url hash to use for cache lookup
    urlhash,ext = generate_url_hash(urlpath)
    if file_ext:
        ext = file_ext # override file ext if provided
    temp_filename = DL_CACHE_PREFIX + urlhash + ext
    
    # lookup urlpath among cached downloads
    cache = get_dl_cache()
    if temp_filename in cache:
        # return temp file from cache
        print(f'getting {urlpath} from cache')
        print(f'(cache size {len(cache)})')
        temp_path = cache[temp_filename]
    else:
        # doesnt exists in cache, download url
        print('downloading to cache', urlpath)
        print(f'(cache size {len(cache)})')
        from urllib.request import Request, urlopen
        import tempfile
        import shutil
        import hashlib
        # open url as fobj
        timeout = 60 * DL_TIMEOUT # mins to secs
        headers = {
            'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36',
            'Connection': 'keep-alive',
        }
        req = Request(urlpath, headers=headers)
        fobj = urlopen(req, timeout=timeout)
        # determine temp file path
        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
        # stream url fobj to temp file
        with open(temp_path, mode='w+b') as temp:
            shutil.copyfileobj(fobj, temp)
        # make sure cache doesn't get too big
        cache_files = list(cache.values()) + [temp_path]
        try:
            cache_files = oldest_to_newest_file_paths(cache_files)
            while len(cache_files) > DL_CACHE_MAX_FILES:
                fil = cache_files.pop(0)
                print('clearing oldest cache file', fil)
                try: os.remove(fil)
                except: pass
        except Exception as err:
            print('WARNING: unable to clear cache:', err)

    # return file path
    print('local file path', temp_path)
    return temp_path

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
    # read shapefile from local file

    # if path_zipped_file is given, add to end of path
    # which is handled natively by pyshp
    if params.get('path_zipped_file', None):
        relpath = params['path_zipped_file']
        params['path'] = f"{params['path']}/{relpath}"

    # get shapefile encoding
    reader_opts = {}
    encoding = params.get('encoding', None)
    if encoding:
        # manually specified
        reader_opts['encoding'] = encoding
    else:
        # otherwise try to autodetect
        encoding = detect_shapefile_encoding(params['path'])
        if encoding:
            reader_opts['encoding'] = encoding
        
    # define nested shapefile groups reading
    def iter_shapefile_groups(reader, group_field=None, group_delim=None, group_index=None, subset=None):
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
            if group_delim:
                key = lambda x: group_delim.join(x[0].split(group_delim)[:group_index+1])
            else:
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
        group_delim = level_def.get('id_delimiter', None)
        group_index = int(level_def['id_index']) if level_def.get('id_index',None) != None else None
        fields = [v for k,v in level_def.items() if k.endswith('_field') and v != None]
        for groupval,_subset in iter_shapefile_groups(reader, group_field, group_delim, group_index, subset):
            # get hardcoded group val if group_field not set
            if not group_field and 'id' in level_def:
                groupval = level_def['id']
            # override all level 0 with a single iso country lookup
            # WARNING: this assumes that id_field is iso code if is set for level0
            if level == 0 and groupval:
                try:
                    if len(groupval) == 2:
                        level_def['name'] = iso3_to_name[iso2_to_3[groupval]]
                    elif len(groupval) == 3:
                        level_def['name'] = iso3_to_name[groupval]
                    else:
                        print(f'Country id {groupval} is not an ISO code, skipping')
                        continue
                except KeyError:
                    print(f'Country id {groupval} could not be found in ISO lookup, skipping')
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
    print('loading shapefile')
    import shapefile
    reader = shapefile.Reader(params['path'], **reader_opts)
    print(reader)
    print('fields:', [f[0] for f in reader.fields])

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

def add_to_db(reader, common, entries, parent=None, depth=0, admins=None, names=None):
    source = common['source']
    start = common['start']
    end = common['end']
    if admins is None:
        admins = []
    if names is None:
        names = []
    save_every = 100  # bulk save when admins gets bigger than X

    def bulk_add(admins, names):
        # copy the lists so that clearing the lists doesn't affect the bulk create
        admins = list(admins)
        names = list(names)
        print(f'--> saving {len(names)} names, {len(admins)} admins...')
        # names
        if names:
            max_id = models.AdminName.objects.all().aggregate(max_id=Max('pk'))['max_id'] or 1
            for i,n in enumerate(names):
                # manually set pk since we're not using save()
                n.pk = max_id + i + 1
            #print(names)
            models.AdminName.objects.bulk_create(names)
        # admins
        max_id = models.Admin.objects.all().aggregate(max_id=Max('pk'))['max_id'] or 1
        for i,x in enumerate(admins):
            # manually set pk since we're not using save()
            x['obj'].pk = max_id + i + 1
            # also manually set bbox
            if x['obj'].geom:
                xmin,ymin,xmax,ymax = x['obj'].geom.bbox()
                x['obj'].minx = xmin
                x['obj'].miny = ymin
                x['obj'].maxx = xmax
                x['obj'].maxy = ymax
        # bulk create lowest depths first, since parent admins must already exist
        depth_key = lambda x: x['depth']
        for _depth,_admins in itertools.groupby(sorted(admins, key=depth_key), key=depth_key):
            #print(_depth, [(x['obj'],x['obj'].parent) for x in _admins])
            models.Admin.objects.bulk_create([x['obj'] for x in _admins])
        # admin-name links
        #print('saved names',names)
        for x in admins:
            #print('name links', x['obj'], [(n.name,n.pk) for n in x['names']])
            x['obj'].names.add(*x['names'])

    for entry in entries:
        #print(entry['item'])

        groupval = entry['item']['id']
        level = entry['item']['level']
        name = entry['item']['name']
        subset = entry['item']['positions']

        # get names
        if not name:
            continue
        
        # first see if name matches any of the yet to be created name objects
        #print('looking for', name)
        name_matches = (n for n in names if n.name==name)
        name_obj = next(name_matches, None)

        # or see if name exists in db
        if name_obj is None:
            try:
                name_obj = models.AdminName.objects.get(name__iexact=name)
                #print('name found', name_obj.name, name_obj.pk)
            except ObjectDoesNotExist:
                name_obj = models.AdminName(name=name)
                names.append(name_obj) #name_obj.save()
                #print('name to be created', name_obj.name, name_obj.pk, names)

        if entry['children']:
            # reached parent node
            print('parent node:', entry['item'])

            # create parent node
            admin = models.Admin(parent=parent, source=source, level=level)
            admins.append({'obj':admin, 'names':[name_obj], 'depth':depth}) #admin.save()
            #admin.names.add(name_obj)

            # process all children one level deeper
            add_to_db(reader, common, entry['children'], parent=admin, depth=depth+1, admins=admins, names=names)

        else:
            # reached leaf node
            #print('leaf node:', entry['item'])
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

            # create admin
            #print('saving')
            geom = WKBGeometry(geom)
            admin = models.Admin(parent=parent, source=source, level=level, 
                                geom=geom, valid_from=start, valid_to=end)
            admins.append({'obj':admin, 'names':[name_obj], 'depth':depth}) #admin.save()
            #admin.names.add(name_obj)

        # bulk add if limit reached
        if len(admins) >= 100:
            print('limit reached')
            bulk_add(admins, names)
            admins[:] = []
            names[:] = []

    # bulk add any remaining objects before exiting the top level
    if depth == 0:
        print('final bulk add')
        bulk_add(admins, names)
        admins[:] = []
        names[:] = []
