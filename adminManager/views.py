from django.shortcuts import render, redirect
from django.db import transaction
from django.forms import modelformset_factory
from django.views.decorators.csrf import csrf_exempt
from django.http.response import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from . import models
from . import forms

from adminImporter.models import DatasetImporter
from adminImporter.forms import DatasetImporterForm

import json

# Create your views here.

@login_required
@permission_required('adminManager.view_adminsource', raise_exception=True)
def datasources(request):
    top_datasets = models.AdminSource.objects.filter(type='DataSource', parent=None)

    from .utils import sources_with_stats
    top_datasets = sources_with_stats([d.pk for d in top_datasets])

    context = {'datasets':top_datasets,
                'add_dataset_form': forms.AdminSourceForm(initial={'type':'DataSource'}),
                }
    return render(request, 'adminManager/sources_data.html', context=context)

@login_required
@permission_required('adminManager.view_adminsource', raise_exception=True)
def datasource(request, pk):
    '''View of a source'''
    src = models.AdminSource.objects.get(pk=pk)
    #importers = src.all_imports()

    #children = [(c,{'admin_count':'X'}) for c in src.children.all()]
    children = src.children_with_stats()
    if children:
        # total status counts for immediate children
        imported = sum(stats.get('status_counts',{}).get('Imported',0) for c,stats in children)
        importing = sum(stats.get('status_counts',{}).get('Importing',0) for c,stats in children)
        failed = sum(stats.get('status_counts',{}).get('Failed',0) for c,stats in children)
        pending = sum(stats.get('status_counts',{}).get('Pending',0) for c,stats in children)
    else:
        # no children, total status counts for self
        imports = list(src.importers.all())
        imported = sum((1 for i in imports if i.import_status == 'Imported'))
        importing = sum((1 for i in imports if i.import_status == 'Importing'))
        failed = sum((1 for i in imports if i.import_status == 'Failed'))
        pending = sum((1 for i in imports if i.import_status == 'Pending'))

    context = {
        'source':src,
        'children':children,
        'boundary_count': src.admin_count(),
        
        'imported': imported,
        'pending': pending,
        'failed': failed,
        'importing': importing,

        'add_dataset_form': forms.AdminSourceForm(initial={'type':'DataSource', 'parent':pk}),
        #'toplevel_geojson':json.dumps({'type':'FeatureCollection','features':[]}),
        #'toplevel_geojson':json.dumps(src.toplevel_geojson())
    }

    print('typ',src,repr(src.type))

    assert src.type == 'DataSource'
    
    return render(request, 'adminManager/source_data.html', context)

@login_required
@permission_required('adminManager.delete_adminsource', raise_exception=True)
def datasource_delete(request, pk):
    '''Delete a source'''
    src = models.AdminSource.objects.get(pk=pk)
    src.delete()
    return redirect('datasets')

#@login_required
#@permission_required('adminmanager.add_adminsource') # requires authentication when using api
@csrf_exempt
def api_datasource_add(request):
    '''API endpoint to add a data source via json data'''

    if request.method == 'POST':
        # load json
        import json
        data = json.loads(request.body.decode("utf-8"))
        print('received',data)

        # load parent if provided
        if data.get('parent', None):
            data['parent'] = models.AdminSource.objects.get(pk=data['parent'])

        # create source
        src = models.AdminSource.objects.create(**data)
        src.save()

        results = {'pk': src.pk}
        return JsonResponse(results)

@login_required
@permission_required('adminManager.add_adminsource', raise_exception=True)
def datasource_add(request):
    if request.method == 'GET':
        # TODO: shouldnt happen, since dataset add is a popup, not a page
        jkllkjljljljlj

        # create empty form
        #form = forms.AdminSourceForm(initial={'type':'DataSource'})
        #context = {'form': form}
        #return render(request, 'adminManager/source_data_add.html', context)

    elif request.method == 'POST':
        # save form data
        data = request.POST
        print(data)

        form = forms.AdminSourceForm(data)
        if form.is_valid():
            form.save()
            source = form.instance
            # add saved source to importer forms data
            # formsetdata = {k:v for k,v in data.items() if k.startswith('form-')}
            # for i in range(int(formsetdata['form-TOTAL_FORMS'])):
            #     formsetdata[f'form-{i}-source'] = source.id
            # save importers
            # DatasetImporterFormset = modelformset_factory(DatasetImporter, 
            #                                             form=DatasetImporterForm,
            #                                             extra=0)
            # importer_forms = DatasetImporterFormset(formsetdata)

            # for import_form in importer_forms:
            #     if import_form.is_valid():
            #         #print(import_form.cleaned_data)
            #         # validate import params
            #         import_params = import_form.cleaned_data['import_params']
            #         if import_params['path']:
            #             # probably should validate some more... 
            #             import_form.save()
            #     else:
            #         # not sure how to deal with invalid forms yet....
            #         raise Exception(f'invalid form: {import_form.errors}')

            #if importer_forms.is_valid():
            #    importer_forms.save()
            #else:
            #    print(importer_forms.errors)
            #    raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')

            return redirect('dataset', source.pk)

        else:
            raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
            return render(request, 'adminManager/source_data_add.html', {'form':form})

@login_required
@permission_required('adminManager.change_adminsource', raise_exception=True)
def datasource_edit(request, pk):
    '''Edit of a data source'''
    src = models.AdminSource.objects.get(pk=pk)
    initial = {'source':src}

    if request.method == 'GET':
        # create editable source form
        form = forms.AdminSourceForm(instance=src)
        # create editable import forms
        DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                    form=DatasetImporterForm,
                                                    extra=10, can_delete=True)
        queryset = src.importers.all()
        importer_forms = DatasetImporterFormset(queryset=queryset, 
                                                initial=[initial]*10) # one for each 'extra' form
        context = {'form': form, 'importer_forms': importer_forms}
        return render(request, 'adminManager/source_data_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)
            form = forms.AdminSourceForm(data, instance=src)
            if form.is_valid():
                form.save()
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
                return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

# not sure if should require permissions or not... 
def api_admin_data(request):
    from django.db import connection
    from django.http import JsonResponse
    import json
    cur = connection.cursor()

    params = request.GET
    source_id = params.get('source', None)
    if source_id:
        # get all child source ids
        #src = models.AdminSource(pk=source_id)
        #all_sources = src.all_children()
        #source_ids = [c.pk for c in all_sources]
        sql = f'''
        WITH RECURSIVE recurs AS
            (
                SELECT id FROM adminManager_adminsource WHERE id = {source_id}

                UNION ALL

                SELECT s.id FROM recurs
                INNER JOIN adminManager_adminsource AS s
                ON s.parent_id = recurs.id
            )
        '''

        # create bbox geom if given
        xmin,ymin,xmax,ymax = params.get('xmin'),params.get('ymin'),params.get('xmax'),params.get('ymax')
        if xmin != None:
            sql += f'''
            ,
            bbox AS
                (SELECT ST_ENVELOPE(MULTIPOINT(POINT({xmin},{ymin}), POINT({xmax},{ymax}))) AS geom)
            '''

        # sql to get admins belonging to sources
        #admins = models.Admin.objects.filter(source__in=source_ids)
        #exclude = params.get('exclude', None)
        #if exclude:
        #    print(exclude)
        #    exclude = list(map(int,exclude.split(',')))
        #    admins = admins.exclude(id__in=exclude)
        
        # custom sql to get admin id and geom as wkt
        # including any filters provided by url params
        #source_ids_string = ','.join(map(str,source_ids)) #','.join(['%s']*len(source_ids))
        #source_ids_string = ' or '.join((f'a.source_id={v}' for v in source_ids))
        admin_table = models.Admin._meta.db_table
        sql += f'''
        select a.id, minx, miny, maxx, maxy
        from {admin_table} as a, recurs as r'''

        # include bbox table if given
        if xmin != None:
            sql += ', bbox as b'

        # where ids match and has geom
        sql += '''
        where a.source_id = r.id
        and minx is not null
        '''

        # sql = '''select count(id)
        #     from (
        # WITH RECURSIVE recurs AS
        #     (
        #         SELECT id FROM adminManager_adminsource WHERE id = 3497

        #         UNION ALL

        #         SELECT s.id FROM recurs
        #         INNER JOIN adminManager_adminsource AS s
        #         ON s.parent_id = recurs.id
        #     )

        # select a.id, minx, miny, maxx, maxy, null as wkt
        # from adminManager_admin as a, recurs as r
        # where minx >= 0 and maxx <= 50
        # and miny >= 0 and maxy <= 30

        # ) as sub
        # '''

        #sql = f'''
        #select count(id)
        #from {admin_table} as a
        #where source_id in (38,39)
        #'''
        
        # limit to bbox if given
        if xmin != None:
            # limit to bbox
            sql += f'''
            and minx < {xmax} and maxx >= {xmin}
            and miny < {ymax} and maxy >= {ymin}
            '''

            # limit to minimum area compared to bbox
            extent_frac = params.get('minimum_extent_fraction', None)
            if extent_frac != None:
                w,h = float(xmax)-float(xmin),float(ymax)-float(ymin)
                dx,dy = w/float(extent_frac), h/float(extent_frac)
                #min_area = dx * dy
                #sql += f'''
                #and st_area(st_envelope(geom)) > {min_area}
                #'''
                #sql += f'''
                #and ((maxx-minx) * (maxy-miny)) > {min_area}
                #'''
                sql += f'''
                and (maxx-minx) > {dx} and (maxy-miny) > {dy}
                '''
        
            # exclude geoms completely containing the bbox
            # TODO: the bbox contains is fine,
            # but the st_within or st_contains is very slow... 
            #and not mbrcontains(a.geom, b.geom)
            #and not st_contains(a.geom, b.geom)
            # sql += f'''
            # and not (
            #     {xmin} >= minx and {xmax} <= maxx
            #     and {ymin} >= miny and {ymax} <= maxy
            # )
            # and not st_within(b.geom, a.geom)
            # '''

        # debug
        #print(sql)
        #cur.execute(f'explain {sql}')
        #for row in cur: print(row)
        #fdsfdsf
        
        if params.get('summary_only', None):
            # sql summarize
            sql = f'''
            select count(id),min(minx),min(miny),max(maxx),max(maxy)
            from ({sql}) as sub
            '''
            print(sql)
            cur.execute(sql)
            count,xmin,ymin,xmax,ymax = cur.fetchone()
            print('summarized',count)
            if count:
                bbox = xmin,ymin,xmax,ymax
            else:
                bbox = None
            # result data
            result = {'count':count, 'bbox':bbox, 'result':[]}

        else:
            # get admins
            # NOTE: doing anything with geom in the same query as subsetting
            # ...is incredibly slow, seems like it causes it to stop using the index? 
            # ...or actually seems like the problem is some very large geoms...
            # sql = '''
            # WITH RECURSIVE recurs AS
            #     (
            #         SELECT id FROM adminManager_adminsource WHERE id = 3497

            #         UNION ALL

            #         SELECT s.id FROM recurs
            #         INNER JOIN adminManager_adminsource AS s
            #         ON s.parent_id = recurs.id
            #     ),
            # subset as (
            #     select a.id
            #     from adminManager_admin as a, recurs as r
            #     where a.source_id = r.id
            #     and minx is not null

            #         and minx < 179.99999999999923 and maxx >= -180.00000000000077
            #         and miny < 80.76018215516447 and maxy >= -85.05112877980659

            #             and (maxx-minx) > 18.0 and (maxy-miny) > 8.290565546748553
            # )
            # select id from subset
            # '''

            # determine wkt expr
            if params.get('geom', 'true') == 'true':
                # convert geom to bbox if geom size is too large
                geom_size_limit = params.get('geom_size_limit', 100000)
                wkt_expr = f'''
                    case when length(geom) < {geom_size_limit} then st_aswkt(geom)
                    else st_aswkt(st_envelope(multipoint(point(minx,miny), point(maxx,maxy)))) end
                '''
                # experiment bbox for each poly part
                # '''
                # with firstgeom as (
                #     select id, 1 as num, st_geometryn(geom, 1) as subgeom
                #     from adminManager_admin
                #     where st_geometrytype(geom) = 'MultiGeometry'
                #     limit 1
                # ),
                # recursive polyparts as (
                #     select * from firstgeom
                #     union all
                #     select a.id, num+1, st_geometryn(a.geom, num+1) as subgeom
                #     from polyparts as p, adminManager_admin as a
                #     where a.id = p.id
                #     and (num+1) <= st_numgeometries(a.geom)
                # )
                # select * from polyparts
                # limit 10
                # '''
            else:
                wkt_expr = 'null'

            # get ids
            print(sql)
            cur.execute(sql)
            source_ids = [r[0] for r in cur]
            print(f'fetched {len(source_ids)} admin ids from db')

            if source_ids:
                # get geoms one by one via pymysql to see which geoms are the problem
                # from core.settings import DATABASES
                # import pymysql
                # db = DATABASES['default']
                # connection = pymysql.connect(host=db['HOST'],
                #                  user=db['USER'],
                #                  password=db['PASSWORD'],
                #                  database=db['NAME'],
                #                  port=db['PORT'],
                #                  #charset=db['OPTIONS']['CHARSET'],
                #                  ssl=db['OPTIONS'],
                #                  ) #cursorclass=pymysql.cursors.DictCursor)
                # admins = []
                # for id in source_ids: 
                #     print(id)
                #     sql = f'select id,level,minx,miny,maxx,maxy,st_aswkt(geom) from adminManager_admin where id = {id}'
                #     cur.execute(sql)
                #     row = list(cur)[0]
                #     admins.append(row)

                # get geoms one by one via django to see which geoms are the problem
                #sql = f'select id from adminManager_admin where id in {tuple(source_ids)}'
                #print(sql)
                #cur.execute(sql) #, source_ids)
                #print(connection, cur)
                # admins = []
                # for id in source_ids: 
                #     print(id)
                #     #a = models.Admin.objects.get(id=id)
                #     #print(a, a.geom.geom_type, len(a.geom.wkb))
                #     sql = f'''
                #     select id,level,minx,miny,maxx,maxy,
                #     (case when length(geom) < 100000 then st_aswkt(geom)
                #     else st_aswkt(st_envelope(multipoint(point(minx,miny), point(maxx,maxy)))) end) as wkt
                #     from adminManager_admin where id = {id}
                #     '''
                #     cur.execute(sql)
                #     a = list(cur)[0]
                #     admins.append(a)

                # get all geoms via id in list
                #sql = f'select id,level,minx,miny,maxx,maxy,st_aswkt(geom) from adminManager_admin where id in {tuple(source_ids)}'
                source_ids_string = ','.join(map(str,source_ids))
                sql = f'''
                    select id,level,minx,miny,maxx,maxy,({wkt_expr}) as wkt
                    from adminManager_admin where id in ({source_ids_string})
                    '''
                print(sql)
                cur.execute(sql) #, source_ids)
                admins = cur

                # try to django filter admin objs
                # admins = models.Admin.objects.filter(id__in=source_ids)
                # for a in admins: print(a)
                # sdfsdfs
                
                #admin_ids = list(admin_geoms.keys())
                #admins = models.Admin.objects.filter(id__in=admin_ids)
                
                # create result
                print('building results')
                result_list = [];
                for row in admins:
                    id, level, xmin, ymin, xmax, ymax, wkt = row
                    info = {'level':level, 'id':id, 'bbox':[xmin,ymin,xmax,ymax]}
                    info['wkt'] = wkt
                    result_list.append(info)
                key = lambda x: x['level']
                result_list = sorted(result_list, key=key, reverse=True)

                # get total bbox
                xmins,ymins,xmaxs,ymaxs = zip(*(info['bbox'] for info in result_list))
                bbox = min(xmins),min(ymins),max(xmaxs),max(ymaxs)

                # return data
                result = {'count':len(result_list), 'bbox':bbox, 'result':result_list}

            else:
                result = {'count':0, 'bbox':None, 'result':[]}

        # return as json
        print('returning')
        return JsonResponse(result)

# not sure if should require permissions or not... 
def api_admin_data(request):
    from django.db import connection
    from django.http import JsonResponse
    import json
    cur = connection.cursor()

    params = request.GET
    sql = ''

    # decide universe of admins
    ids = params.get('ids', '')
    source_id = params.get('source', None)
    admin_table = models.Admin._meta.db_table

    # A. limit to specified admin ids
    if ids:
        sql += f'''
        WITH admins AS (
            select a.id, minx, miny, maxx, maxy
            from {admin_table} as a
            where a.id in ({ids})
            and minx is not null
        '''

    # B. limit to admins by source
    elif source_id:
        # get all child source ids
        sql += f'''
        WITH RECURSIVE
        recurs AS (
                SELECT id FROM adminManager_adminsource WHERE id = {source_id}

                UNION ALL

                SELECT s.id FROM recurs
                INNER JOIN adminManager_adminsource AS s
                ON s.parent_id = recurs.id
        )'''

        # sql to get admins belonging to sources and has geom
        admin_table = models.Admin._meta.db_table
        sql += f'''
        WITH admins AS (
            select a.id, minx, miny, maxx, maxy
            from {admin_table} as a, recurs as r
            where a.source_id = r.id
            and minx is not null
        '''

    # C. don't limit, consider all admins
    else:
        sql += f'''
        WITH admins AS (
            select a.id, minx, miny, maxx, maxy
            from {admin_table} as a
            where minx is not null
        '''

    # limit to bbox if given
    xmin,ymin,xmax,ymax = params.get('xmin'),params.get('ymin'),params.get('xmax'),params.get('ymax')
    if xmin != None:
        # limit to bbox
        sql += f'''
        and minx < {xmax} and maxx >= {xmin}
        and miny < {ymax} and maxy >= {ymin}
        '''
    
    # close admin table
    sql += '\n)'

    # limit to minimum area compared to bbox
    # doesnt filter, only marks and renders simplified bbox geom (later)
    extent_frac = params.get('minimum_extent_fraction', None)
    if xmin != None and extent_frac != None:
        w,h = float(xmax)-float(xmin),float(ymax)-float(ymin)
        dx,dy = w/float(extent_frac), h/float(extent_frac)
        sql += f'''
        , admins2 as (
        select *, ((maxx-minx) > {dx} and (maxy-miny) > {dy}) as isvisible
        from admins
        )
        '''
    else:
        sql += f'''
        , admins2 as (
        select *, TRUE as isvisible
        from admins
        )
        '''

    if params.get('summary_only', None):
        # sql summarize
        sql = f'''
        select count(id),min(minx),min(miny),max(maxx),max(maxy)
        from ({sql}) as sub
        '''
        print(sql)
        cur.execute(sql)
        count,xmin,ymin,xmax,ymax = cur.fetchone()
        print('summarized',count)
        if count:
            bbox = xmin,ymin,xmax,ymax
        else:
            bbox = None
        # result data
        result = {'count':count, 'bbox':bbox, 'result':[]}

    else:
        # get admins

        # determine wkt expr
        if params.get('geom', 'true') == 'true':
            # convert geom to bbox if geom size is too large
            # or if bbox is not visible
            geom_size_limit = params.get('geom_size_limit', 100000)
            wkt_expr = f'''
                case when isvisible and length(geom) < {geom_size_limit} 
                then st_aswkt(geom)
                else st_aswkt(st_envelope(multipoint(point(a.minx,a.miny), point(a.maxx,a.maxy)))) end
            '''
        else:
            wkt_expr = 'null'

        # based on previous filtered tables, get original admin info incl geom wkt
        sql += f'''
        select orig.id,orig.level,a.minx,a.miny,a.maxx,a.maxy,a.isvisible,({wkt_expr}) as wkt
        from adminManager_admin as orig
        inner join admins2 as a
        on a.id = orig.id
        '''

        # execute
        print(sql)
        cur.execute(sql)

        # create result
        print('building results')
        result_list = [];
        for row in cur:
            id, level, xmin, ymin, xmax, ymax, isvisible, wkt = row
            info = {'level':level, 'id':id, 'bbox':[xmin,ymin,xmax,ymax], 'isvisible':isvisible}
            info['wkt'] = wkt
            result_list.append(info)
        key = lambda x: x['level']
        result_list = sorted(result_list, key=key, reverse=True)

        # get total bbox
        if result_list:
            xmins,ymins,xmaxs,ymaxs = zip(*(info['bbox'] for info in result_list))
            bbox = min(xmins),min(ymins),max(xmaxs),max(ymaxs)
        else:
            bbox = [None,None,None,None]

        # return data
        result = {'count':len(result_list), 'bbox':bbox, 'result':result_list}

    # return as json
    print('returning')
    return JsonResponse(result)
