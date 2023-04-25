"""gbTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('datasource/clear/<int:pk>/', views.datasource_clear, name='datasource_clear'),
    path('datasource/import/<int:pk>/', views.datasource_import, name='datasource_import'),
    path('datasource/importers/edit/<int:pk>/', views.datasource_importers_edit, name='datasource_importers_edit'),
    #path('datasource/import_all/', views.datasource_import_all, name='datasource_import_all'),
]
