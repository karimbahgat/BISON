from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Count, Min, Max

import json

def home(request):
    context = {}
    return render(request, 'home.html', context=context)
