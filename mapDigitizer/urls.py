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
    path('maps/', views.mapsources, name='maps'),
    path('maps/add', views.mapsource_add, name='map_add'),
    path('maps/<int:pk>/', views.mapsource, name='map'),
    path('maps/<int:pk>/edit', views.mapsource_edit, name='map_edit'),
    path('digitize_map/<int:pk>/', views.digitize_map, name='digitize_map'),
    path('label_map/<int:pk>/', views.label_map, name='label_map'),
]
