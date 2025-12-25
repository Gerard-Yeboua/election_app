# apps/dashboard/urls.py
from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('carte-bureaux/', views.carte_bureaux, name='carte_bureaux'),
    path('api/stats-temps-reel/', views.statistiques_temps_reel, name='stats_temps_reel'),
]