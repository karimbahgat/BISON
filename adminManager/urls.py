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
    path('datasets/', views.datasources, name='datasets'),
    path('datasets/<int:pk>/', views.datasource, name='dataset'),
    path('datasets/add/', views.datasource_add, name='dataset_add'),
    path('datasets/<int:pk>/edit/', views.datasource_edit, name='dataset_edit'),
    path('datasets/<int:pk>/delete/', views.datasource_delete, name='dataset_delete'),
    path('api/admins/', views.api_admin_data, name='api_admin_data'),
    path('api/datasets/add/', views.api_datasource_add, name='api_dataset_add'),
]
