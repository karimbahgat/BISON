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

def api_search_name(request):
    # this is only a simple search for a single name
    # no hierarchical input
    search = request.GET.get('search')
    
    # search admins that match on name (lowest level)
    names = models.AdminName.objects.filter(name__icontains=search)
    names.prefetch_related('admins')

    # calc search relevance metric (percent difference)
    search_len = len(search)
    names = names.annotate(shortest=Least(Length('name'), Value(search_len)),
                            longest=Greatest(Length('name'), Value(search_len)),
                            )
    names = names.annotate(simil=F('shortest') / Cast('longest', FloatField()) )
    names = names.order_by('-simil')

    # use a difference cutoff (eg only matches above 0.5 perc)?
    # ... 

    # serialize
    def serialize(m):
        admins = [a.id for a in m.admins.all()]
        return {'id':m.id, 'name':m.name, 'simil':m.simil, 'admins':admins}
    results = [serialize(n) for n in names]

    # return
    data = {'search':search, 'count':len(results), 'results':results}
    return JsonResponse(data)

def api_search_name_hierarchy(request):
    '''
    # get all matches at lowest level
    # for next search level, add a dummy if each match has a parent w that name
    # for next search level, add a dummy if all previous levels has parent w that name

    # create list of each level in search query
    # eg [bærum, viken, norway]
    # to evaluate a potential match, goal is to create a list of string overlaps for each level
    # eg [bærnes, vika, norway] => [3, 3, 6]
    # (each string overlap is based on the level with the highest string percentage)
    # then calc highest possible string overlap, as max(totalSearchChars, totalMatchChars)
    # eg max((5+5+6), (6+4+6)) = max(16, 16) = 16
    # ultimately from this create a single match metric as percent of total possible shared chars
    # eg (3 + 3 + 6) / 16 = 12 / 16 = 0.75

    # procedure is:
    # - for each match candidate
    #   - for each search level
    #     - set match score to highest matching level in match candidate
    
    # example match: [bærnes, vika, norway]
    #         [bærnes] [vika] [norway]
    #[bærum]     3       0        0
    #[viken]     0       3        0
    #[norway]    0       0        6

    # example match: [viken, norway]
    #         [viken] [norway]
    #[bærum]     0       0
    #[viken]     3       0
    #[norway]    0       6

    # example match: kolsås, bærum, viken, norway

    # example match: norway, minnesota, united states

    '''

    # hierarchical input
    search_query = request.GET.get('search')
    searches = [s.strip() for s in search_query.split(',')]

    # (hacky one-time creation of case insensitive name index)
    #from django.db import connection
    #with connection.cursor() as cursor:
    #    cursor.execute("create index 'adminManager_adminName_name_nocollate_idx' on 'adminManager_adminName' ('name' collate nocase)")
    #    print('created')

    # search admins that match on name (lowest level)
    matches = models.Admin.objects.filter(names__name__istartswith=searches[0], 
                                        geom__isnull=False) # only those with geoms
    matches = list(matches)
    print('db fetched',len(matches))

    # functions
    def calc_name_match(name1, name2):
        name1,name2 = name1.lower(),name2.lower()
        if (name1 in name2 or name2 in name1):
            name1_length,name2_length = len(name1),len(name2)
            percent_match = min(name1_length, name2_length) / max(name1_length, name2_length)
        else:
            percent_match = 0.0
        #print('name match',name1,name2,percent_match)
        return percent_match

    def calc_highest_name_match(search, parent):
        name_matches = [(n,calc_name_match(search,n.name))
                        for n in parent.names.all()]
        best_name,best_name_match = sorted(name_matches, key=lambda x: x[1])[-1]
        return best_name,best_name_match

    def calc_best_parent_match(search, candidate):
        parents = candidate.get_all_parents()
        # sort parents by highest name match and get highest one
        parent_matches = [(p, calc_highest_name_match(search, p))
                          for p in parents]
        #print('parent_matches',parent_matches)
        best_parent,(best_name,best_name_match) = sorted(parent_matches, key=lambda x: x[1][1])[-1]
        return best_parent,best_name,best_name_match

    def calc_maximum_char_overlap(searches, candidate):
        parents = candidate.get_all_parents()
        total_search_chars = sum([len(s) for s in searches])
        total_match_chars = sum([max([len(n.name) for n in p.names.all()]) for p in candidate.get_all_parents()])
        return max(total_search_chars, total_match_chars)

    # for each potential match
    results = []
    for m in matches:

        # calc search overlaps for each search level
        best_level_names = []
        best_level_overlaps = []
        for search in searches:
            #print('search',search)

            # NOTE: this recursive get all parents is the most expensive part
            best_parent,best_name,best_name_match = calc_best_parent_match(search, m)
            best_level_names.append(best_name)
            #print('best level name',best_name.name,best_name_match)

            best_name_overlap = min(len(search), len(best_name.name)) if best_name_match else 0.0
            best_level_overlaps.append(best_name_overlap)
            #print('best level overlap',best_name.name,best_name_overlap)

        # calc total string overlap (ie intersection)
        total_char_overlap = sum(best_level_overlaps)
        
        # calc max string overlap (ie union)
        max_char_overlap = calc_maximum_char_overlap(searches, m)

        # calc similarity as intersection / union
        #print('isec/union', total_char_overlap, max_char_overlap)
        simil = total_char_overlap / max_char_overlap

        # serialize and add to results
        serialized = m.serialize(geom=False)
        serialized['simil'] = simil
        results.append(serialized)
    print('python calc and serialized',len(results))

    # sort by similarity
    results = sorted(results, key=lambda r: r['simil'], reverse=True)

    # return
    data = {'search':search_query, 'count':len(results), 'results':results}
    return JsonResponse(data)

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

    # find admins with matching names for each hierarchy subquery
    thresh = 0.3 # text match threshold
    name_queries = []
    for search in searches:
        sub = models.Admin.objects.values('id', 'level', 'parent', 'names__name', 'minx')
        sub = sub.filter(names__name__istartswith=search)
        sub = sub.annotate(simil=Value(float(len(search)))/Cast(Length('names__name'), FloatField()))
        sub = sub.filter(simil__gte=thresh)
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

    # mayyyybe do some magic so we only keep admins where all hierarchy levels satisfy the thresh? 
    # ...

    # aggregate to leaf nodes along with additional columns we want for final results
    # including creating an aggregate simil score for all hierarchy simil scores
    sql += '''
, final AS (
    SELECT j.leaf_id AS id, 
        a.valid_from, a.valid_to,
        a.minx, a.miny, a.maxx, a.maxy,
        SUM(j.simil) AS simil,
        GROUP_CONCAT(j.id) AS hierarchy_ids, 
        GROUP_CONCAT(j.names) AS hierarchy_names, 
        GROUP_CONCAT(j.level) AS hierarchy_levels
    FROM adminManager_admin AS a
    INNER JOIN joined_names AS j
    ON a.id = j.leaf_id
    GROUP BY j.leaf_id
)
'''

    # add in sources
    # ... 

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
    results = []
    for row in iter_table(sql, sql_params, 'final'):
        id,valid_from,valid_to, \
            xmin,ymin,xmax,ymax, \
            simil,hierarchy_ids,hierarchy_names,hierarchy_levels = row
        hierarchy = []
        zipped = zip(hierarchy_ids.split(','), 
                    hierarchy_names.split(','),
                    hierarchy_levels.split(','))
        zipped = sorted(zipped, key=lambda z: z[-1], reverse=True) # sort by decreasing level
        for hid,hnames,hlevel in zipped:
            hnames = hnames.split('|')
            hdict = {'id':hid, 'level':hlevel, 'names':hnames}
            hierarchy.append(hdict)
        entry = {'id':id,
                'hierarchy':hierarchy,
                'source':{'name':'', 'id':''},
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
    xmin,ymin,xmax,ymax = admin.minx,admin.miny,admin.maxx,admin.maxy
    #print(xmin,ymin,xmax,ymax)

    # find all other admins whose bbox overlap
    matches = models.Admin.objects.filter(minx__lte=xmax, maxx__gte=xmin,
                                          miny__lte=ymax, maxy__gte=ymin)
    matches = matches.exclude(source=admin.source)
    print(matches.count(), 'bbox overlaps')

    # calculate geom overlap/similarity
    # PAPER NOTE: scatterplot of bbox overlap vs geom overlap
    def getshp(obj, simplify=False):
        shp = wkb_loads(obj.geom.wkb)
        if simplify:
            return shp.simplify(0.001)
        else:
            return shp
    def similarity(shp1, shp2):
        if not shp1.intersects(shp2):
            return 0
        isec = shp1.intersection(shp2)
        union = shp1.union(shp2)
        simil = isec.area / union.area
        return simil
    from time import time
    t=time()
    shp = getshp(admin, simplify=True)
    matches = [(m,similarity(shp, getshp(m)))
                for m in matches]
    print('comparisons finished in',time()-t,'seconds')

    # sort simil by source, only return best simil in source

    # maybe also quick filter based on total area of B, or
    # combined area of A plus B (compared to intersection area of
    # another we can know the max possible overlap and so can skip)

    # filter to overlapping geoms
    matches = [(m,simil) for m,simil in matches
                if simil > 0.01]

    # sort by similarity
    matches = sorted(matches, key=lambda x: -x[1])

    # return list of admins as json
    results = []
    for m,simil in matches:
        entry = m.serialize(geom=False)
        entry['simil'] = simil
        #print(admin,m,simil)
        results.append(entry)
    print(len(results), 'geom overlaps serialized')

    data = {'count': len(results), 'results':results}
    return JsonResponse(data)

def api_get_best_source_matches(request, id):
    admin = models.Admin.objects.get(pk=id)
    xmin,ymin,xmax,ymax = admin.minx,admin.miny,admin.maxx,admin.maxy
    #print(xmin,ymin,xmax,ymax)

    # find all other admins whose bbox overlap
    from time import time
    t = time()
    matches = models.Admin.objects.filter(minx__lte=xmax, maxx__gte=xmin,
                                          miny__lte=ymax, maxy__gte=ymin)
    matches = matches.exclude(source=admin.source)
    print(matches.count(), 'bbox overlaps')

    # calc bbox simil
    ## bbox xoverlap = max(minx,xmin) - min(maxx,xmax)
    ## bbox yoverlap = max(miny,ymin) - min(maxy,ymax)
    matches = matches.annotate(xoverlap=Greatest('minx',Value(xmin)) - Least('maxx',Value(xmax)),
                                yoverlap=Greatest('miny',Value(ymin)) - Least('maxy',Value(ymax)),
                                xunion=Least('minx',Value(xmin)) - Greatest('maxx',Value(xmax)),
                                yunion=Least('miny',Value(ymin)) - Greatest('maxy',Value(ymax)),
                                )
    ## bbox overlap = xoverlap * yoverlap
    matches = matches.annotate(union=F('xunion') * F('yunion'),
                                overlap=F('xoverlap') * F('yoverlap'),
                                )
    ## bbox similarity
    matches = matches.annotate(bbox_simil=F('overlap')/F('union'))

    # get the admin w highest bbox simil in each source group
    matches = list(matches.values('id', 'names__name', 'source__id', 'source__name', 'bbox_simil'))
    best_matches = {}
    key = lambda m: m['source__id']
    grouped = itertools.groupby(sorted(matches, key=key), key=key)
    for src_id,group in grouped:
        #print(src)
        group = list(group)
        most_similar = sorted(group, key=lambda m: m['bbox_simil'], reverse=True)
        #print(most_similar)
        best_match = most_similar[0]
        best_matches[src_id] = best_match
    print('bbox overlaps done')

    # calc true overlap for the best source matches
    def getshp(obj, simplify=False):
        shp = wkb_loads(obj.geom.wkb)
        if simplify:
            return shp.simplify(0.001)
        else:
            return shp
    def similarity(shp1, shp2):
        if not shp1.intersects(shp2):
            return 0
        isec = shp1.intersection(shp2)
        union = shp1.union(shp2)
        simil = isec.area / union.area
        return simil
    # begin
    shp = getshp(admin, simplify=True)
    for src_id,best in best_matches.items():
        print(src_id,best)
        best_obj = models.Admin.objects.get(pk=best['id'])
        best['obj'] = best_obj
        best['simil'] = similarity(shp, getshp(best_obj))
    print('comparisons finished in',time()-t,'seconds')

    # return as list of sources with best match info, sorted by simil
    key = lambda v: v['simil']
    results = sorted(best_matches.values(), key=key, reverse=True)

    # get list of sources with best match admin, sorted by simil
    # filter by similarity thresh
    key = lambda v: v['simil']
    thresh = 0.05
    results = []
    for best_match in sorted(best_matches.values(), key=key, reverse=True):
        m = best_match['obj']
        entry = m.serialize(geom=False)
        entry['bbox_simil'] = best_match['bbox_simil']
        entry['simil'] = best_match['simil']
        if entry['simil'] >= thresh:
            #print(admin,m,simil)
            results.append(entry)
    print(len(results), 'geom overlaps serialized')

    # calc total cross-source agreement
    # ie prob that a randomly chosen point in the selected geom
    # will land in the matched geom from a randomly chosen source
    # is calc as the average of probabilities
    # this assumes equal probability of choosing each source
    simils = [e['simil'] for e in results]
    agreement = sum(simils) / len(simils) if simils else 1.0

    # return as json
    data = {'count': len(results), 'results':results, 'agreement':agreement}
    return JsonResponse(data)
