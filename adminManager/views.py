from django.shortcuts import render, redirect
from django.db import transaction

from . import models
from . import forms

from adminImporter.forms import DatasetImporterForm

import json

# Create your views here.

def sources(request):
    datasets = models.AdminSource.objects.filter(type='DataSource')
    context = {'datasets':datasets,
                'add_dataset_form': forms.AdminSourceForm(initial={'type':'DataSource'}),
                'import_params_form': DatasetImporterForm(),
                }
    return render(request, 'adminManager/sources.html', context=context)

def source(request, pk):
    '''View of a source'''
    src = models.AdminSource.objects.get(pk=pk)
    toplevel_refs = src.admins.filter(parent=None)
    context = {'source':src, 'toplevel_refs':toplevel_refs}

    print('typ',src,repr(src.type))
    
    if src.type == 'DataSource':
        import_params = src.importer.import_params
        try: import_params = json.dumps(import_params, indent=4)
        except: pass
        context['import_params'] = import_params
        return render(request, 'adminManager/source_data.html', context)
        
    elif src.type == 'MapSource':
        levels = src.admins.all().values_list('level').distinct()
        levels = [lvl[0] for lvl in levels]
        context['levels'] = sorted(levels)
        return render(request, 'adminManager/source_map.html', context)

def datasource_add(request):
    if request.method == 'GET':
        # create empty form
        form = forms.AdminSourceForm(initial={'type':'DataSource'})
        context = {'form': form}
        return render(request, 'adminManager/source_data_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)
            form = forms.AdminSourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                # save importer
                from adminImporter.models import DatasetImporter
                print(data['import_params'])
                import_params = json.loads(data['import_params'])
                importer = DatasetImporter(source=source, import_params=import_params)
                importer.save()
                return redirect('source', source.pk)
            else:
                raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
                return render(request, 'adminManager/source_data_add.html', {'form':form})

def datasource_edit(request, pk):
    '''Edit of a data source'''
    src = models.AdminSource.objects.get(pk=pk)

    if request.method == 'GET':
        # create empty form
        form = forms.AdminSourceForm(instance=src)
        import_params_form = DatasetImporterForm(instance=src.importer)
        context = {'form': form, 'import_params_form': import_params_form}
        return render(request, 'adminManager/source_data_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.AdminSourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                # save importer
                importer = src.importer
                importer.import_params = json.loads(data['import_params'])
                importer.save()
                return redirect('source', src.pk)
            else:
                return render(request, 'adminManager/source_data_edit.html', {'form':form})

