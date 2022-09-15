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

    # strategy
    # maybe start searching highest parent and find results
    # then from those results, search the next level among the children of those
    # and keep narrowing at each step
    
    # first search main name (lowest level)
    names = models.AdminName.objects.filter(name__icontains=search)

    # calc search relevance metric (percent difference)
    search_len = len(search)
    names = names.annotate(perc_diff=Abs(Length('name') - Value(search_len))  / Value(search_len, output_field=FloatField()),
                            admins=Concat('admin__id'))
    names = names.order_by('perc_diff')
    # ... 

    # use a difference cutoff (eg only matches above 0.5 perc)
    # ... 

    # serialize
    results = [n for n in names.values()]
    #results = [a.serialize() for a in names]
    #for a in results:
    #    del a['geom'] # dont return geom

    # return
    data = {'count':len(results), 'results':results}
    return JsonResponse(data)
