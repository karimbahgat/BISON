from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Min, Max

from adminManager import models

import json

# def home(request):
#     dataset_count = models.AdminSource.objects.filter(type='DataSource').count()
#     map_count = models.AdminSource.objects.filter(type='MapSource').count()
#     admin_count = models.Admin.objects.all().count()
#     context = {'dataset_count':dataset_count,
#                 'map_count':map_count,
#                 'admin_count':admin_count}
#     return render(request, 'home.html', context=context)

def home(request):
    return redirect('boundarylookup')
