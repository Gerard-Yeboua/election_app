# apps/statistic/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from statistic.viewsets import (
    CacheStatistiqueViewSet,
    StatistiqueViewSet,
    StatistiqueRegionViewSet,
    StatistiqueBureauViewSet,
    StatistiqueCandidatViewSet,
    StatistiqueTimelineViewSet,
    StatistiquePerformanceViewSet,
    SnapshotQuotidienViewSet
)

app_name = 'statistic'

router = DefaultRouter()
router.register(r'cache', CacheStatistiqueViewSet, basename='cache')
router.register(r'stats', StatistiqueViewSet, basename='stats')
router.register(r'regions', StatistiqueRegionViewSet, basename='regions')
router.register(r'bureaux', StatistiqueBureauViewSet, basename='bureaux')
router.register(r'candidats', StatistiqueCandidatViewSet, basename='candidats')
router.register(r'timeline', StatistiqueTimelineViewSet, basename='timeline')
router.register(r'performance', StatistiquePerformanceViewSet, basename='performance')
router.register(r'snapshots', SnapshotQuotidienViewSet, basename='snapshots')

urlpatterns = [
    path('', include(router.urls)),
]

# apps/statistics/urls.py - Ajouter aux URLs API existantes
from django.urls import path
from statistic import views



# URLs pour les vues Django classiques
urlpatterns_django = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('region/<uuid:region_id>/', views.stats_region, name='region'),
    path('national/', views.stats_national, name='national'),
    path('candidat/<uuid:candidat_id>/', views.stats_candidat, name='candidat'),
    path('comparaison-candidats/', views.comparaison_candidats, name='comparaison_candidats'),
    path('tendances/', views.tendances, name='tendances'),
    path('refresh-cache/', views.refresh_cache, name='refresh_cache'),
]