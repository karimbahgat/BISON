from django.shortcuts import render, redirect
from django.db import transaction
from django.forms import modelformset_factory

from . import models
from . import forms

from adminImporter.models import DatasetImporter
from adminImporter.forms import DatasetImporterForm

import json

# Create your views here.

def datasources(request):
    datasets = models.AdminSource.objects.filter(type='DataSource')
    DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                        form=DatasetImporterForm,
                                        extra=1)
    importer_forms = DatasetImporterFormset(queryset=models.AdminSource.objects.none())
    context = {'datasets':datasets,
                'add_dataset_form': forms.AdminSourceForm(initial={'type':'DataSource'}),
                'importer_forms': importer_forms,
                }
    return render(request, 'adminManager/sources_data.html', context=context)

def datasource(request, pk):
    '''View of a source'''
    src = models.AdminSource.objects.get(pk=pk)
    toplevel_refs = src.admins.filter(parent=None)
    context = {'source':src, 'toplevel_refs':toplevel_refs}

    print('typ',src,repr(src.type))

    assert src.type == 'DataSource'
    
    return render(request, 'adminManager/source_data.html', context)

def datasource_add(request):
    if request.method == 'GET':
        # TODO: shouldnt happen, since dataset add is a popup, not a page
        jkllkjljljljlj

        # create empty form
        #form = forms.AdminSourceForm(initial={'type':'DataSource'})
        #context = {'form': form}
        #return render(request, 'adminManager/source_data_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)

            form = forms.AdminSourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                # add saved source to importer forms data
                formsetdata = {k:v for k,v in data.items() if k.startswith('form-')}
                for i in range(int(formsetdata['form-TOTAL_FORMS'])):
                    formsetdata[f'form-{i}-source'] = source.id
                # save importers
                DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                            form=DatasetImporterForm,
                                                            extra=0)
                importer_forms = DatasetImporterFormset(formsetdata)
                if importer_forms.is_valid():
                    importer_forms.save()
                else:
                    print(importer_forms.errors)
                    raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')

                return redirect('dataset', source.pk)

            else:
                raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
                return render(request, 'adminManager/source_data_add.html', {'form':form})

def datasource_edit(request, pk):
    '''Edit of a data source'''
    src = models.AdminSource.objects.get(pk=pk)

    if request.method == 'GET':
        # create editable source form
        form = forms.AdminSourceForm(instance=src)
        # create editable import forms
        DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                    form=DatasetImporterForm,
                                                    extra=0)
        queryset = DatasetImporter.objects.filter(source=src)
        importer_forms = DatasetImporterFormset(queryset=queryset)
        context = {'form': form, 'importer_forms': importer_forms}
        return render(request, 'adminManager/source_data_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            print(data)
            form = forms.AdminSourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                # save importers
                DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                            form=DatasetImporterForm,
                                                            extra=0)
                importer_forms = DatasetImporterFormset(data)
                if importer_forms.is_valid():
                    importer_forms.save()
                else:
                    print(importer_forms.errors)
                    return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

                return redirect('dataset', src.pk)

            else:
                return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

