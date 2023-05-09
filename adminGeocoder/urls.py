"""core URL Configuration

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
from django.urls import path, include

from . import views

urlpatterns = [
    path('lookup', views.boundarylookup, name='boundarylookup'),
    path('api/search/name', views.api_search_name, name='api_search_name'),
    path('api/search/name_hierarchy', views.api_search_name_hierarchy, name='api_search_name_hierarchy'),
    path('api/get_admin/<str:id>/', views.api_get_admin, name='api_get_admin'),
    path('api/get_geom/<str:id>/', views.api_get_geom, name='api_get_geom'),
    path('api/get_similar_admins/<int:id>/', views.api_get_similar_admins, name='api_get_similar_admins'),
    path('api/get_best_source_matches/<int:id>/', views.api_get_best_source_matches, name='api_get_best_source_matches'),
]
