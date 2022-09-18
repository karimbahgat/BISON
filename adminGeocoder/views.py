from django.shortcuts import render
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import Field, Value, IntegerField, FloatField, Prefetch
from django.db.models.functions import Length, Abs, Concat

from adminManager import models

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
    names = names.annotate(perc_diff=Abs(Length('name') - Value(search_len))  / Value(search_len, output_field=FloatField()),
                            )
    names = names.order_by('perc_diff')

    # use a difference cutoff (eg only matches above 0.5 perc)?
    # ... 

    # serialize
    def serialize(m):
        admins = [a.id for a in m.admins.all()]
        return {'id':m.id, 'name':m.name, 'perc_diff':m.perc_diff, 'admins':admins}
    results = [serialize(n) for n in names]

    # return
    data = {'search':search, 'count':len(results), 'results':results}
    return JsonResponse(data)

def api_get_admin(request, id):
    admin = models.Admin.objects.get(pk=id)
    data = admin.serialize()
    print(data)
    return JsonResponse(data)
