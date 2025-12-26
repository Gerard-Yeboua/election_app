# apps/statistics/filters.py
from django_filters import rest_framework as filters
from statistics.models import (
    CacheStatistique, StatistiqueTimeline, SnapshotQuotidien
)


class CacheStatistiqueFilter(filters.FilterSet):
    """Filtres pour CacheStatistique"""
    
    type_entite = filters.ChoiceFilter(choices=CacheStatistique.TYPE_ENTITE_CHOICES)
    type_statistique = filters.ChoiceFilter(choices=CacheStatistique.TYPE_STATISTIQUE_CHOICES)
    is_valid = filters.BooleanFilter()
    date_calcul_after = filters.DateTimeFilter(field_name='date_calcul', lookup_expr='gte')
    date_calcul_before = filters.DateTimeFilter(field_name='date_calcul', lookup_expr='lte')
    
    class Meta:
        model = CacheStatistique
        fields = ['type_entite', 'type_statistique', 'is_valid']


class StatistiqueTimelineFilter(filters.FilterSet):
    """Filtres pour StatistiqueTimeline"""
    
    type_timeline = filters.ChoiceFilter(choices=StatistiqueTimeline.TYPE_CHOICES)
    granularite = filters.ChoiceFilter(choices=StatistiqueTimeline.GRANULARITE_CHOICES)
    date_debut_after = filters.DateTimeFilter(field_name='date_debut', lookup_expr='gte')
    date_fin_before = filters.DateTimeFilter(field_name='date_fin', lookup_expr='lte')
    
    class Meta:
        model = StatistiqueTimeline
        fields = ['type_timeline', 'granularite', 'region']


class SnapshotQuotidienFilter(filters.FilterSet):
    """Filtres pour SnapshotQuotidien"""
    
    date_after = filters.DateFilter(field_name='date', lookup_expr='gte')
    date_before = filters.DateFilter(field_name='date', lookup_expr='lte')
    
    class Meta:
        model = SnapshotQuotidien
        fields = ['date']