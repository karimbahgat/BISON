from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone

import json

from adminManager.models import AdminSource
from adminManager import forms
#from .models import MapDigitizer

# Create your views here.

def mapsources(request):
    maps = AdminSource.objects.filter(type='MapSource')
    context = {'maps':maps,
                'add_map_form': forms.AdminSourceForm(initial={'type':'MapSource'}),
                }
    return render(request, 'mapDigitizer/sources_map.html', context=context)

def mapsource(request, pk):
    '''View of a map'''
    src = AdminSource.objects.get(pk=pk)
    toplevel_refs = src.admins.filter(parent=None)
    context = {'source':src, 'toplevel_refs':toplevel_refs}

    assert src.type == 'MapSource'

    levels = src.admins.all().values_list('level').distinct()
    levels = [lvl[0] for lvl in levels]
    context['levels'] = sorted(levels)
    return render(request, 'mapDigitizer/source_map.html', context)

def mapsource_add(request):
    if request.method == 'GET':
        # create empty form
        form = forms.AdminSourceForm(initial={'type':'DataSource'})
        context = {'form': form}
        return render(request, 'mapDigitizer/source_map_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)
            form = forms.AdminSourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                return redirect('map', source.pk)
            else:
                raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
                return render(request, 'adminManager/source_data_add.html', {'form':form})

def mapsource_edit(request, pk):
    '''Edit of a map source'''
    src = AdminSource.objects.get(pk=pk)

    if request.method == 'GET':
        # create empty form
        form = forms.AdminSourceForm(instance=src)
        context = {'form': form, 'source':src}
        return render(request, 'mapDigitizer/source_map_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.AdminSourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                return redirect('map', src.pk)
            else:
                raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
                return render(request, 'adminManager/source_data_edit.html', {'form':form})

def digitize_map(request, pk):
    source = AdminSource.objects.get(pk=pk)
    
    #if request.method == 'GET':
    #    # show current state of the map
    #    return render(request, 'digitize_map.html', {'source':source})

    if request.method == 'POST':
        # receive and save digitized map data
        with transaction.atomic():
            # save raw digitizing data
            data = request.POST['data']
            data = json.loads(data)
            digitizer,created = MapDigitizer.objects.get_or_create(source=source)
            digitizer.digitized_data = data
            digitizer.last_digitized = timezone.now()
            digitizer.save()
            # attempt to create snapshots from digitized line data
            digitizer.build()

        return redirect('source', source.pk)

def label_map(request, pk):
    source = AdminSource.objects.get(pk=pk)

    if request.method == 'POST':
        # receive and save digitized map data
        with transaction.atomic():
            # load labelling data
            data = request.POST['data']
            data = json.loads(data)
            # update snapshot labels
            digitizer = MapDigitizer.objects.get(source=source)
            digitizer.update_names(data)

        return redirect('source', source.pk)
