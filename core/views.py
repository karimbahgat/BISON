from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Min, Max

from adminManager import models

import json

def home(request):

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
    #         x.save()

    sources = models.AdminSource.objects.filter(type='DataSource')
    context = {'sources':sources}
    return render(request, 'home.html', context=context)
