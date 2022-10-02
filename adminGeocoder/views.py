from django.shortcuts import render
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import F, Value, IntegerField, FloatField, Prefetch
from django.db.models.functions import Length, Abs, Concat, Greatest, Least, Cast

from adminManager import models

from shapely.wkb import loads as wkb_loads

# Create your views here.

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

def api_get_admin(request, id):
    geom_string = request.GET.get('geom', 'true')
    if geom_string.lower() in ('true','1'):
        geom = True
    elif geom_string.lower() in ('false','0'):
        geom = False
    else:
        raise ValueError('geom param must be one of true,false,1,0')
    admin = models.Admin.objects.get(pk=id)
    data = admin.serialize(geom=geom)
    return JsonResponse(data)

def api_get_similar_admins(request, id):
    admin = models.Admin.objects.get(pk=id)
    xmin,ymin,xmax,ymax = admin.geom.bbox()
    #print(xmin,ymin,xmax,ymax)

    # find all other admins whose bbox overlap
    matches = models.Admin.objects.exclude(pk=id)
    matches = matches.filter(maxx__gte=xmin, minx__lte=xmax,
                             maxy__gte=ymin, miny__lte=ymax)
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
    shp = getshp(admin, simplify=True)
    matches = [(m,similarity(shp, getshp(m)))
                for m in matches]

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
    print(len(results), 'geom overlaps')

    data = {'count': len(results), 'results':results}
    return JsonResponse(data)
