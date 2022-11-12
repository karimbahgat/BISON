from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Min, Max

from adminManager import models

import json

def home(request):
    source_count = models.AdminSource.objects.all().count()
    admin_count = models.Admin.objects.all().count()
    context = {'source_count':source_count,
                'admin_count':admin_count}
    return render(request, 'home.html', context=context)
