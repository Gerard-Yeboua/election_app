# statistics/serializers.py
from rest_framework import serializers
from statistic.models import (
    CacheStatistique, StatistiqueRegion, StatistiqueBureau,
    StatistiqueCandidat, StatistiqueTimeline, StatistiquePerformance,
    SnapshotQuotidien
)
from geography.models import Region, Departement, Commune, BureauVote
from pv.models import Candidat
from accounts.models import User


# ============================================================
# SERIALIZERS GÉOGRAPHIE
# ============================================================

class RegionSerializer(serializers.ModelSerializer):
    """Serializer pour Region"""
    
    class Meta:
        model = Region
        fields = ['id', 'code_region', 'nom_region', 'population', 'superficie']


class BureauVoteSerializer(serializers.ModelSerializer):
    """Serializer pour BureauVote"""
    
    lieu_vote_nom = serializers.CharField(source='lieu_vote.nom_lv', read_only=True)
    commune = serializers.CharField(
        source='lieu_vote.sous_prefecture.commune.nom_commune',
        read_only=True
    )
    
    class Meta:
        model = BureauVote
        fields = [
            'id', 'code_bv', 'nom_bv', 'lieu_vote_nom', 'commune',
            'nombre_inscrits', 'est_actif'
        ]


# ============================================================
# SERIALIZERS STATISTIQUES
# ============================================================

class CacheStatistiqueSerializer(serializers.ModelSerializer):
    """Serializer pour CacheStatistique"""
    
    est_valide = serializers.BooleanField(read_only=True)
    est_expire = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CacheStatistique
        fields = [
            'id', 'type_entite', 'entite_id', 'type_statistique',
            'cache_key', 'data', 'date_calcul', 'duree_calcul_ms',
            'ttl_minutes', 'date_expiration', 'est_valide', 'est_expire',
            'is_valid', 'hit_count', 'last_accessed', 'version'
        ]
        read_only_fields = [
            'cache_key', 'date_calcul', 'date_expiration',
            'hit_count', 'last_accessed', 'version'
        ]


class StatistiqueRegionSerializer(serializers.ModelSerializer):
    """Serializer pour StatistiqueRegion"""
    
    region = RegionSerializer(read_only=True)
    region_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = StatistiqueRegion
        fields = '__all__'


class StatistiqueBureauSerializer(serializers.ModelSerializer):
    """Serializer pour StatistiqueBureau"""
    
    bureau = BureauVoteSerializer(read_only=True)
    bureau_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = StatistiqueBureau
        fields = '__all__'


class StatistiqueCandidatSerializer(serializers.ModelSerializer):
    """Serializer pour StatistiqueCandidat"""
    
    candidat_nom = serializers.CharField(source='candidat.nom_complet', read_only=True)
    candidat_parti = serializers.CharField(source='candidat.parti_politique', read_only=True)
    
    class Meta:
        model = StatistiqueCandidat
        fields = '__all__'


class StatistiqueTimelineSerializer(serializers.ModelSerializer):
    """Serializer pour StatistiqueTimeline"""
    
    region_nom = serializers.CharField(source='region.nom_region', read_only=True, allow_null=True)
    
    class Meta:
        model = StatistiqueTimeline
        fields = '__all__'


class StatistiquePerformanceSerializer(serializers.ModelSerializer):
    """Serializer pour StatistiquePerformance"""
    
    user_nom = serializers.CharField(source='user.nom_complet', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = StatistiquePerformance
        fields = '__all__'


class SnapshotQuotidienSerializer(serializers.ModelSerializer):
    """Serializer pour SnapshotQuotidien"""
    
    class Meta:
        model = SnapshotQuotidien
        fields = '__all__'


# ============================================================
# SERIALIZERS POUR LES VUES PERSONNALISÉES
# ============================================================

class StatsGeneralesSerializer(serializers.Serializer):
    """Serializer pour les statistiques générales"""
    
    total_bureaux = serializers.IntegerField()
    total_inscrits = serializers.IntegerField()
    total_pv_soumis = serializers.IntegerField()
    total_pv_valides = serializers.IntegerField()
    taux_soumission = serializers.FloatField()
    taux_validation = serializers.FloatField()
    total_votants = serializers.IntegerField()
    taux_participation = serializers.FloatField()
    total_incidents = serializers.IntegerField()
    incidents_ouverts = serializers.IntegerField()


class StatsParticipationSerializer(serializers.Serializer):
    """Serializer pour les statistiques de participation"""
    
    total_inscrits = serializers.IntegerField()
    total_votants = serializers.IntegerField()
    total_exprimes = serializers.IntegerField()
    total_nuls = serializers.IntegerField()
    total_blancs = serializers.IntegerField()
    taux_participation = serializers.FloatField()
    taux_nuls = serializers.FloatField()
    taux_blancs = serializers.FloatField()


class StatsIncidentsSerializer(serializers.Serializer):
    """Serializer pour les statistiques d'incidents"""
    
    total = serializers.IntegerField()
    ouverts = serializers.IntegerField()
    en_cours = serializers.IntegerField()
    traites = serializers.IntegerField()
    clos = serializers.IntegerField()
    urgents = serializers.IntegerField()
    par_categorie = serializers.DictField()


class ResultatCandidatSerializer(serializers.Serializer):
    """Serializer pour les résultats d'un candidat"""
    
    candidat = serializers.CharField()
    parti = serializers.CharField()
    numero = serializers.IntegerField()
    voix = serializers.IntegerField()
    pourcentage = serializers.FloatField()


class StatsDashboardSerializer(serializers.Serializer):
    """Serializer pour le dashboard principal"""
    
    stats_generales = StatsGeneralesSerializer()
    stats_participation = StatsParticipationSerializer()
    stats_incidents = StatsIncidentsSerializer()
    top_candidats = ResultatCandidatSerializer(many=True)
    evolution_soumissions = serializers.ListField()
    alertes = serializers.ListField()


class StatsRegionDetailSerializer(serializers.Serializer):
    """Serializer détaillé pour les stats d'une région"""
    
    region = RegionSerializer()
    stats_bureaux = serializers.DictField()
    stats_pv = serializers.DictField()
    stats_participation = StatsParticipationSerializer()
    stats_incidents = StatsIncidentsSerializer()
    resultats_candidats = ResultatCandidatSerializer(many=True)
    stats_par_departement = serializers.ListField()


class TimelinePointSerializer(serializers.Serializer):
    """Serializer pour un point de la timeline"""
    
    date = serializers.DateTimeField()
    valeur = serializers.IntegerField()


class TimelineSerializer(serializers.Serializer):
    """Serializer pour une timeline complète"""
    
    type = serializers.CharField()
    granularite = serializers.CharField()
    date_debut = serializers.DateTimeField()
    date_fin = serializers.DateTimeField()
    data_points = TimelinePointSerializer(many=True)
    total = serializers.IntegerField()
    moyenne = serializers.FloatField()
    minimum = serializers.IntegerField()
    maximum = serializers.IntegerField()


class ComparaisonRegionsSerializer(serializers.Serializer):
    """Serializer pour comparer plusieurs régions"""
    
    region = serializers.CharField()
    taux_participation = serializers.FloatField()
    taux_soumission = serializers.FloatField()
    total_incidents = serializers.IntegerField()
    candidat_tete = serializers.CharField()