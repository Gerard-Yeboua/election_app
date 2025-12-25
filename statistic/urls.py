# apps/statistics/urls.py
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

app_name = 'statistics'

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