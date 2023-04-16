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
                                        extra=10)
    importer_forms = DatasetImporterFormset(queryset=models.AdminSource.objects.none())
    context = {'datasets':datasets,
                'add_dataset_form': forms.AdminSourceForm(initial={'type':'DataSource'}),
                'importer_forms': importer_forms,
                }
    return render(request, 'adminManager/sources_data.html', context=context)

def datasource(request, pk):
    '''View of a source'''
    src = models.AdminSource.objects.get(pk=pk)
    processed_count = src.importers.filter(import_status__in=["Imported","Failed"]).count()
    fail_count = src.importers.filter(import_status="Failed").count()
    context = {
        'source':src,
        'processed_count':processed_count,
        'fail_count':fail_count,
        'toplevel_geojson':json.dumps(src.toplevel_geojson()),
    }

    print('typ',src,repr(src.type))

    assert src.type == 'DataSource'
    
    return render(request, 'adminManager/source_data.html', context)

def datasource_delete(request, pk):
    '''Delete a source'''
    src = models.AdminSource.objects.get(pk=pk)
    src.delete()
    return redirect('datasets')

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

                for import_form in importer_forms:
                    if import_form.is_valid():
                        #print(import_form.cleaned_data)
                        # validate import params
                        import_params = import_form.cleaned_data['import_params']
                        if import_params['path']:
                            # probably should validate some more... 
                            import_form.save()
                    else:
                        # not sure how to deal with invalid forms yet....
                        raise Exception(f'invalid form: {import_form.errors}')

                #if importer_forms.is_valid():
                #    importer_forms.save()
                #else:
                #    print(importer_forms.errors)
                #    raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')

                return redirect('dataset', source.pk)

            else:
                raise NotImplementedError('Invalid form handling needs to be added by redirecting to sources.html with popup')
                return render(request, 'adminManager/source_data_add.html', {'form':form})

def datasource_edit(request, pk):
    '''Edit of a data source'''
    src = models.AdminSource.objects.get(pk=pk)
    initial = {'source':src}

    if request.method == 'GET':
        # create editable source form
        form = forms.AdminSourceForm(instance=src)
        # create editable import forms
        DatasetImporterFormset = modelformset_factory(DatasetImporter, 
                                                    form=DatasetImporterForm,
                                                    extra=10, can_delete=True)
        queryset = src.importers.all()
        importer_forms = DatasetImporterFormset(queryset=queryset, 
                                                initial=[initial]*10) # one for each 'extra' form
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
                                                            extra=0, can_delete=True)
                importer_forms = DatasetImporterFormset(data)
                for import_form in importer_forms:
                    if import_form.is_valid():
                        if import_form.has_changed():
                            #print(import_form.cleaned_data)
                            # check for deletion
                            if import_form.cleaned_data['DELETE']:
                                import_form.instance.delete()
                                continue
                            # validate import params
                            import_params = import_form.cleaned_data['import_params']
                            if import_params['path']:
                                # probably should validate some more... 
                                import_form.save()
                    else:
                        # not sure how to deal with invalid forms yet....
                        raise Exception(f'invalid form: {import_form.errors}')
                        
                #if importer_forms.is_valid():
                #    importer_forms.save()
                #else:
                #    print(importer_forms.errors)
                #    raise Exception('Need better input form error handling...')
                #    return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

                return redirect('dataset', src.pk)

            else:
                return render(request, 'adminManager/source_data_edit.html', {'form':form, 'importer_forms':importer_forms})

