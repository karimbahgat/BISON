from django.shortcuts import render
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import F, Value, IntegerField, FloatField, Prefetch
from django.db.models.functions import Length, Abs, Concat, Greatest, Least, Cast, Upper

from adminManager import models

from shapely.wkb import loads as wkb_loads

import itertools

# Create your views here.

def boundarylookup(request):
    sources = models.AdminSource.objects.filter(type='DataSource')
    context = {'sources':sources}
    return render(request, 'adminGeocoder/boundarylookup.html', context=context)

def api_search_name_hierarchy(request):
    # hierarchical input
    search_query = request.GET.get('search')
    searches = [s.strip() for s in search_query.split(',')]
    sql_params = []
    sql = 'WITH RECURSIVE'

    def iter_table(sql, sql_params, table):
        from django.db import connection
        sql = sql + f'SELECT * FROM {table}'
        print(sql)
        curs = connection.cursor()
        curs.execute(sql, sql_params)
        for row in curs:
            yield row

    # find admins with matching names for each hierarchy subquery (above thresh)
    simil_thresh = 0.3 # text match threshold
    name_queries = []
    for search in searches:
        sub = models.Admin.objects.values('id', 'level', 'parent', 'names__name', 'source_id', 'minx')
        sub = sub.filter(names__name__istartswith=search)
        sub = sub.annotate(simil=Value(float(len(search)))/Cast(Length('names__name'), FloatField()))
        sub = sub.filter(simil__gte=simil_thresh)
        query = str(sub.query).replace(f'{search}%', "%s")
        sql_params.append(search+'%') # important to add the wildcard at end
        name_queries.append(query)
    full_name_query = '\nUNION\n'.join(name_queries)
    sql += f'\nmatches AS ({full_name_query})'

    # recursive retrieve all parent admins to construct hierarchy for each leaf node in the matches
    # start with leafs (those with geom/bbox)
    # then recursively join all admins that match the parent_id of previous admins
    # this gives a full tree for every leaf node and therefore duplicates for all parent nodes shared by multiple leaf nodes
    sql += '''
, recurs AS (
    SELECT id AS leaf_id, id, parent_id, level FROM matches WHERE minx IS NOT NULL
    UNION ALL
    SELECT r.leaf_id, a.id, a.parent_id, a.level FROM adminManager_admin AS a
    INNER JOIN recurs AS r
    ON r.parent_id = a.id
)'''

    # join these to the matches
    # (CASE WHEN matches.simil >= 0 THEN matches.simil ELSE 0.0 END) AS simil
    sql += '''
, joined AS (
    SELECT recurs.*, matches.simil
    FROM recurs LEFT JOIN matches ON matches.id = recurs.id
)
'''

    # join these to names
    # multiple names separated by pipe |
    # collapsed to every unique leaf_id,adminid combination
    sql += f'''
, joined_names AS (
    SELECT j.*, GROUP_CONCAT(n.name SEPARATOR '|') AS names
    FROM joined AS j
    INNER JOIN adminManager_admin_names AS link
    ON j.id = link.admin_id 
    INNER JOIN adminManager_adminname AS n
    ON link.adminname_id = n.id
    GROUP BY j.leaf_id, j.id
)
'''

    # mayyyybe do some magic so we only keep admins where all hierarchy levels satisfy the thresh? 
    # ...

    # aggregate to leaf nodes along with additional columns we want for final results
    # including creating an aggregate simil score for all hierarchy simil scores
    sql += '''
, final AS (
    SELECT j.leaf_id AS id, a.source_id,
        a.valid_from, a.valid_to,
        a.minx, a.miny, a.maxx, a.maxy,
        SUM(j.simil) AS simil,
        MIN(j.simil) AS simil_min,
        SUM(j.simil >= 0) AS simil_count,
        GROUP_CONCAT(j.id) AS hierarchy_ids,
        GROUP_CONCAT(j.names) AS hierarchy_names,
        GROUP_CONCAT(j.level) AS hierarchy_levels
    FROM adminManager_admin AS a
    INNER JOIN joined_names AS j
    ON a.id = j.leaf_id
    GROUP BY j.leaf_id
)
'''

    # add in lineres
    # ... 

    # create final results structure
    # dct = {'id':self.pk,
    #         'hierarchy':hierarchy,
    #         'source':{'name':source_name, 'id':source.pk},
    #         'valid_from':self.valid_from,
    #         'valid_to':self.valid_to,
    #         'lineres':self.lineres,
    #         }
    # also 'simil' text match score
    
    #for row in iter_table(sql, sql_params, 'sourceparents_agg'):
    #    print(row)
    #fdsfds
    
    results = []
    rows = list(iter_table(sql, sql_params, 'final'))
    source_ids = [r[1] for r in rows]
    source_lookup = _get_source_names(source_ids)
    for row in rows:
        id,source_id, \
            valid_from,valid_to, \
            xmin,ymin,xmax,ymax, \
            simil,simil_min,simil_count, \
            hierarchy_ids,hierarchy_names,hierarchy_levels = row
        # ignore matches not all search components had a match (num of matched admins must match search components)
        if simil_count < len(searches):
            print('at least one search component didnt have a match, skipping', hierarchy_names, simil_min)
            continue
        # ignore matches where max adm level is below num of search components
        lvls = [int(lvl) for lvl in hierarchy_levels.split(',')]
        if (max(lvls)+1) < len(searches):
            print('match adm level lower than number of search components, skipping', hierarchy_names, lvls)
            continue
        # name simil as percent of highest possible score (highest count of search input vs admin parents)
        count = len(lvls)
        simil_max_possible = max(count, len(searches))
        simil = float(simil) / float(simil_max_possible)
        # build hierarchy
        hierarchy = []
        zipped = zip(hierarchy_ids.split(','), 
                    hierarchy_names.split(','),
                    hierarchy_levels.split(','))
        zipped = sorted(zipped, key=lambda z: z[-1], reverse=True) # sort by decreasing level
        for hid,hnames,hlevel in zipped:
            hnames = hnames.split('|')
            hdict = {'id':hid, 'level':hlevel, 'names':hnames}
            hierarchy.append(hdict)
        # make entry
        source_names = source_lookup[source_id]
        source_names = ' - '.join(source_names.split('|'))
        entry = {'id':id,
                'hierarchy':hierarchy,
                'source':{'name':source_names, 'id':source_id},
                'valid_from':valid_from,
                'valid_to':valid_to,
                'simil':float(simil),
                'lineres':-99.0,
                'bbox':[xmin,ymin,xmax,ymax],
                }
        #print('-->',entry)
        results.append(entry)
    print('calc and serialized',len(results))

    # sort by similarity
    results = sorted(results, key=lambda r: r['simil'], reverse=True)

    # return
    data = {'search':search_query, 'count':len(results), 'results':results}
    return JsonResponse(data)

def _get_source_names(ids):

    if not ids:
        return {}

    def iter_table(sql, sql_params, table):
        from django.db import connection
        sql = sql + f'SELECT * FROM {table}'
        print(sql)
        curs = connection.cursor()
        curs.execute(sql, sql_params)
        return curs

    # recursive get all source names starting with the match source
    source_ids_string = ','.join((str(id) for id in ids))
    sql = f'''with recursive
    sourceparents AS (
        SELECT s.id AS leaf_id, s.id, s.name, s.parent_id, 0 AS source_level
        FROM adminManager_adminsource AS s
        WHERE s.id IN ({source_ids_string})

        UNION ALL
        
        SELECT p.leaf_id, s.id, s.name, s.parent_id, (p.source_level + 1) AS source_level
        FROM adminManager_adminsource AS s
        INNER JOIN sourceparents AS p
        ON s.id = p.parent_id
    )
    '''
    sql += '''
    , sourceparents_agg AS (
        SELECT leaf_id AS source_id, GROUP_CONCAT(name ORDER BY source_level DESC SEPARATOR '|') AS source_names
        FROM sourceparents
        GROUP BY leaf_id
    )
    '''
    lookup = {id:names for id,names in iter_table(sql, None, 'sourceparents_agg')}
    return lookup

def api_get_admin(request, id):
    geom_string = request.GET.get('geom', 'true')
    if geom_string.lower() in ('true','1'):
        geom = True
    elif geom_string.lower() in ('false','0'):
        geom = False
    else:
        raise ValueError('geom param must be one of true,false,1,0')

    if ',' in id:
        ids = [int(_id) for _id in id.split(',')]
        admins = models.Admin.objects.filter(pk__in=ids)
        # returned as list
        data = [admin.serialize(geom=geom) for admin in admins]
    else:
        id = int(id)
        admin = models.Admin.objects.get(pk=id)
        # returned as a single dict
        data = admin.serialize(geom=geom)

    return JsonResponse(data, safe=False)

def api_get_geom(request, id):
    if ',' in id:
        ids = [int(_id) for _id in id.split(',')]
        admins = models.Admin.objects.filter(pk__in=ids)
        # returned as list
        data = [admin.geom.__geo_interface__ for admin in admins]
    else:
        id = int(id)
        admin = models.Admin.objects.get(pk=id)
        # returned as a single dict
        data = admin.geom.__geo_interface__

    return JsonResponse(data, safe=False)

def api_get_similar_admins(request, id):
    admin = models.Admin.objects.get(pk=id)
    from time import time
    t=time()
    simil_thresh = 0.50
    sql = 'with recursive'

    def iter_table(sql, sql_params, table):
        from django.db import connection
        sql = sql + f'SELECT * FROM {table}'
        print(sql)
        print('GO!')
        curs = connection.cursor()
        curs.execute(sql, sql_params)
        return curs

    def iter_sql(sql, sql_params):
        from django.db import connection
        print(sql)
        print('GO!')
        curs = connection.cursor()
        curs.execute(sql, sql_params)
        return curs

    # find all other admins whose bbox overlap (excl self)
    #xmin,ymin,xmax,ymax = admin.minx,admin.miny,admin.maxx,admin.maxy
    #print(xmin,ymin,xmax,ymax)
    sql += f'''
    current as (
        select * from adminManager_admin
        where id = {id}
    )
    , bboxoverlap as (
        select 
            a.*
        from adminManager_admin as a
        where a.minx <= {admin.maxx} and a.maxx >= {admin.minx}
        and a.miny <= {admin.maxy} and a.maxy >= {admin.miny}
        and a.id != {id}
    )'''

    # filter to minimum approx bbox overlap/similarity
    sql += f'''
    , bboxsimils_prep as (
        select
            a.id,
            (greatest(a.minx, {admin.minx}) - least(a.maxx, {admin.maxx})) as xoverlap,
            (greatest(a.miny, {admin.miny}) - least(a.maxy, {admin.maxy})) as yoverlap,
            (least(a.minx, {admin.minx}) - greatest(a.maxx, {admin.maxx})) as xunion,
            (least(a.miny, {admin.miny}) - greatest(a.maxy, {admin.maxy})) as yunion
        from bboxoverlap as a
    )
    , bboxsimils as (
        select
            id,
            ((xoverlap * yoverlap) / (xunion * yunion)) as bbox_simil
        from bboxsimils_prep
    )
    '''
    
    # filter to real geom overlap/similarity
    # 1: calc intersection and union
    sql += f'''
    , simils_prep as (
        select 
            b.*, 
            a.geom, a.level, a.parent_id, a.minx,
            st_intersection(a.geom, c.geom) as isec,
            st_union(a.geom, c.geom) as unio
        from bboxsimils as b, adminManager_admin as a, current as c
        where b.id = a.id
        and bbox_simil >= {simil_thresh}
        and st_intersects(a.geom, c.geom)
    )
    '''
    # 2: calc simil
    sql += f'''
    , simils as (
        select
            *,
            case 
                when st_geometrytype(isec) like '%POLYGON'
                    and st_geometrytype(unio) like '%POLYGON'
                then (st_area(isec) / st_area(unio))
                else null
            end as simil
        from simils_prep
    )
    '''
    # 3: get final matches by filtering on simil
    sql += f'''
    , matches as (
        select *
        from simils
        where simil >= {simil_thresh}
        order by simil desc
    )
    '''
    #sql += 'select id,st_geometrytype(isec),st_geometrytype(unio),bbox_simil,simil from simils'
    # TODO: for now doesnt filter by simil, only bbox_simil
    #sql += f'''
    #select id,geom,bbox_simil from simils
    #order by bbox_simil desc
    #'''

    # get all leaf parents
    sql += '''
    , recurs AS (
        SELECT id AS leaf_id, id, parent_id, level FROM matches WHERE minx IS NOT NULL
        UNION ALL
        SELECT r.leaf_id, a.id, a.parent_id, a.level FROM adminManager_admin AS a
        INNER JOIN recurs AS r
        ON r.parent_id = a.id
    )'''

    # join these to the matches
    sql += '''
    , joined AS (
        SELECT recurs.*, matches.simil FROM recurs LEFT JOIN matches ON matches.id = recurs.id
    )
    '''

    # join these to names
    # multiple names separated by pipe |
    # collapsed to every unique leaf_id,adminid combination
    sql += f'''
    , joined_names AS (
        SELECT j.*, GROUP_CONCAT(n.name SEPARATOR '|') AS names
        FROM joined AS j
        INNER JOIN adminManager_admin_names AS link
        ON j.id = link.admin_id 
        INNER JOIN adminManager_adminname AS n
        ON link.adminname_id = n.id
        GROUP BY j.leaf_id, j.id
    )
    '''

    # aggregate to leaf nodes along with additional columns we want for final results
    # including creating an aggregate simil score for all hierarchy simil scores
    sql += '''
    , final AS (
        SELECT j.leaf_id AS id, a.source_id,
            a.valid_from, a.valid_to,
            a.geom,
            a.minx, a.miny, a.maxx, a.maxy,
            AVG(j.simil) AS simil,
            GROUP_CONCAT(j.id) AS hierarchy_ids, 
            GROUP_CONCAT(j.names) AS hierarchy_names, 
            GROUP_CONCAT(j.level) AS hierarchy_levels
        FROM adminManager_admin AS a
        INNER JOIN joined_names AS j
        ON a.id = j.leaf_id
        GROUP BY j.leaf_id
    )
    '''

    # execute
    try: 
        matches = list(iter_table(sql, None, 'final'))
        #matches = list(iter_sql(sql, None))
        print('comparisons finished in',time()-t,'seconds')
    except Exception as err:
        print('ERROR executing sql:', err)
        data = {'count': 0, 'results':[], 'error':str(err)}
        return JsonResponse(data)

    # return list of admins as json
    results = []
    source_ids = [r[1] for r in matches]
    source_lookup = _get_source_names(source_ids)
    for row in matches:
        # print([repr(v)[:100] for v in row])
        id, source_id, \
            valid_from,valid_to, \
            geom,xmin,ymin,xmax,ymax, \
            simil, \
            hierarchy_ids,hierarchy_names,hierarchy_levels = row
        if not geom:
            print('weird, null geom, skipping')
            continue
        
        # temp
        # id,geom,simil = row
        # valid_from = valid_to = None
        # xmin=ymin=xmax=ymax = None
        # hierarchy_ids = f'{id}'
        # hierarchy_names = 'Dummy Name'
        # hierarchy_levels = '1'

        hierarchy = []
        zipped = zip(hierarchy_ids.split(','), 
                    hierarchy_names.split(','),
                    hierarchy_levels.split(','))
        zipped = sorted(zipped, key=lambda z: z[-1], reverse=True) # sort by decreasing level
        for hid,hnames,hlevel in zipped:
            hnames = hnames.split('|')
            hdict = {'id':hid, 'level':hlevel, 'names':hnames}
            hierarchy.append(hdict)

        from adminManager.geometry import WKBGeometry
        source_names = source_lookup[source_id]
        source_names = ' - '.join(source_names.split('|'))
        entry = {'id':id,
                'hierarchy':hierarchy,
                'source':{'name':source_names, 'id':source_id},
                'valid_from':valid_from,
                'valid_to':valid_to,
                'simil':float(simil),
                'lineres':-99.0,
                'bbox':[xmin,ymin,xmax,ymax],
                'geom':WKBGeometry(geom[4:]).__geo_interface__,
                }
        #print('-->',entry)
        results.append(entry)
    print(len(results), 'geom overlaps serialized')

    data = {'count': len(results), 'results':results}
    return JsonResponse(data)

