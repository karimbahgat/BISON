from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Min, Max

from adminManager import models

import json

def home(request):

    # print('home')
    # for adm in models.Admin.objects.filter(names__name='Afghanistan'): #source__name='GADM v4.0.4', geom__isnull=True):
    #     print(adm, adm.geom, len(adm.geom.wkb))
    #     if adm.geom.wkb:
    #         print(adm.geom.bbox(),(adm.minx,adm.miny))

    # one-time hack to set bbox for existing db entries
    # from django.db import transaction
    # with transaction.atomic():
    #     all = models.Admin.objects.all()
    #     count = all.count()
    #     print('count',count)
    #     nxt = incr = 1000
    #     for i,x in enumerate(all):
    #         if i > nxt:
    #             print(i, 'of', count)
    #             nxt += incr
    #         if x.geom and x.geom.wkb and x.minx is None:
    #             x.save(update_fields=['minx','miny','maxx','maxy'])

    sources = models.AdminSource.objects.filter(type='DataSource')
    context = {'sources':sources}
    return render(request, 'home.html', context=context)
