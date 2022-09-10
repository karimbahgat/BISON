from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models import Count, Min, Max

from adminManager import models

import json

def home(request):
    sources = models.AdminSource.objects.filter(type='DataSource')
    context = {'sources':sources}
    return render(request, 'home.html', context=context)
