# apps/statistics/viewsets.py
from statistics.filters import CacheStatistiqueFilter, StatistiqueTimelineFilter
from statistics.permissions import CanManageCache, CanRefreshCache, CanViewStatistics
from statistics.serializers import BureauVoteSerializer, CacheStatistiqueSerializer, ComparaisonRegionsSerializer, SnapshotQuotidienSerializer, StatistiqueBureauSerializer, StatistiqueCandidatSerializer, StatistiquePerformanceSerializer, StatistiqueRegionSerializer, StatistiqueTimelineSerializer, StatsRegionDetailSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta

from statistics.models import (
    CacheStatistique, StatistiqueRegion, StatistiqueBureau,
    StatistiqueCandidat, StatistiqueTimeline, StatistiquePerformance,
    SnapshotQuotidien
)
from statistics.serializers import *
from statistics.permissions import *
from statistics.filters import *
from statistics.services import StatistiqueService
from geography.models import Region, BureauVote
from pv.models import Candidat


# ============================================================
# VIEWSET CACHE STATISTIQUES
# ============================================================

class CacheStatistiqueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour gérer le cache des statistiques
    """
    queryset = CacheStatistique.objects.all()
    serializer_class = CacheStatistiqueSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CacheStatistiqueFilter
    
    def get_queryset(self):
        """Filtre selon le périmètre de l'utilisateur"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.role == 'SUPER_ADMIN':
            return queryset
        
        elif user.role == 'ADMIN':
            # Filtrer selon le périmètre de l'admin
            if user.region:
                return queryset.filter(
                    type_entite='REGION',
                    entite_id=str(user.region.id)
                )
        
        elif user.role == 'SUPERVISEUR':
            # Superviseur voit uniquement son bureau
            if user.bureau_vote:
                return queryset.filter(
                    type_entite='BUREAU_VOTE',
                    entite_id=str(user.bureau_vote.id)
                )
        
        return queryset.none()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanRefreshCache])
    def refresh(self, request, pk=None):
        """Rafraîchit un cache spécifique"""
        cache = self.get_object()
        service = StatistiqueService()
        
        try:
            data = service.calculer_et_sauvegarder(
                cache.type_entite,
                cache.entite_id,
                cache.type_statistique,
                user=request.user
            )
            
            return Response({
                'status': 'success',
                'message': 'Cache rafraîchi avec succès',
                'data': data
            })
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanManageCache])
    def invalidate(self, request, pk=None):
        """Invalide un cache"""
        cache = self.get_object()
        cache.invalider()
        
        return Response({
            'status': 'success',
            'message': 'Cache invalidé avec succès'
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, CanManageCache])
    def invalidate_pattern(self, request):
        """Invalide tous les caches correspondant à un pattern"""
        pattern = request.data.get('pattern')
        
        if not pattern:
            return Response({
                'status': 'error',
                'message': 'Le paramètre "pattern" est requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        CacheStatistique.invalider_par_pattern(pattern)
        
        return Response({
            'status': 'success',
            'message': f'Caches invalidés pour le pattern: {pattern}'
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques sur le cache"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'valides': queryset.valides().count(),
            'expires': queryset.expires().count(),
            'par_type': {}
        }
        
        # Stats par type
        for type_entite, _ in CacheStatistique.TYPE_ENTITE_CHOICES:
            count = queryset.filter(type_entite=type_entite).count()
            if count > 0:
                stats['par_type'][type_entite] = count
        
        return Response(stats)


# ============================================================
# VIEWSET STATISTIQUES PRINCIPALES
# ============================================================

class StatistiqueViewSet(viewsets.ViewSet):
    """
    ViewSet principal pour accéder aux statistiques
    Utilise le cache automatiquement
    """
    permission_classes = [IsAuthenticated, CanViewStatistics]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Endpoint principal du dashboard
        GET /api/statistics/dashboard/
        """
        user = request.user
        
        # Déterminer le périmètre
        if user.role == 'SUPER_ADMIN':
            # Stats nationales
            data = CacheStatistique.obtenir('NATIONAL', 'national', 'GENERAL')
        elif user.region:
            # Stats régionales
            data = CacheStatistique.obtenir('REGION', str(user.region.id), 'GENERAL')
        elif user.bureau_vote:
            # Stats du bureau
            data = CacheStatistique.obtenir('BUREAU_VOTE', str(user.bureau_vote.id), 'GENERAL')
        else:
            return Response({
                'status': 'error',
                'message': 'Périmètre non défini pour cet utilisateur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='region/(?P<region_id>[^/.]+)')
    def region_stats(self, request, region_id=None):
        """
        Statistiques d'une région
        GET /api/statistics/region/{region_id}/
        """
        # Vérifier les permissions
        if request.user.role != 'SUPER_ADMIN':
            if not request.user.region or str(request.user.region.id) != region_id:
                return Response({
                    'status': 'error',
                    'message': 'Accès non autorisé à cette région'
                }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            region = Region.objects.get(id=region_id)
            data = CacheStatistique.obtenir('REGION', str(region_id), 'GENERAL')
            
            serializer = StatsRegionDetailSerializer({
                'region': region,
                **data
            })
            
            return Response(serializer.data)
        
        except Region.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Région non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='bureau/(?P<bureau_id>[^/.]+)')
    def bureau_stats(self, request, bureau_id=None):
        """
        Statistiques d'un bureau
        GET /api/statistics/bureau/{bureau_id}/
        """
        try:
            bureau = BureauVote.objects.get(id=bureau_id)
            
            # Vérifier les permissions
            if not request.user.peut_acceder_bureau(bureau):
                return Response({
                    'status': 'error',
                    'message': 'Accès non autorisé à ce bureau'
                }, status=status.HTTP_403_FORBIDDEN)
            
            data = CacheStatistique.obtenir('BUREAU_VOTE', str(bureau_id), 'GENERAL')
            
            return Response({
                'bureau': BureauVoteSerializer(bureau).data,
                'statistiques': data
            })
        
        except BureauVote.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Bureau non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='candidat/(?P<candidat_id>[^/.]+)')
    def candidat_stats(self, request, candidat_id=None):
        """
        Statistiques d'un candidat
        GET /api/statistics/candidat/{candidat_id}/
        """
        try:
            candidat = Candidat.objects.get(id=candidat_id)
            data = CacheStatistique.obtenir('CANDIDAT', str(candidat_id), 'RESULTATS')
            
            return Response({
                'candidat': {
                    'id': str(candidat.id),
                    'nom': candidat.nom_complet,
                    'parti': candidat.parti_politique,
                    'numero_ordre': candidat.numero_ordre
                },
                'resultats': data
            })
        
        except Candidat.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Candidat non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        Timeline des événements
        GET /api/statistics/timeline/?type=PV_SOUMISSIONS&jours=7
        """
        type_timeline = request.query_params.get('type', 'PV_SOUMISSIONS')
        jours = int(request.query_params.get('jours', 7))
        
        date_fin = timezone.now()
        date_debut = date_fin - timedelta(days=jours)
        
        service = StatistiqueService()
        
        if type_timeline == 'PV_SOUMISSIONS':
            data = service.calculer_timeline_soumissions_pv(date_debut, date_fin)
        else:
            return Response({
                'status': 'error',
                'message': f'Type de timeline non supporté: {type_timeline}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def comparaison_regions(self, request):
        """
        Compare les statistiques de plusieurs régions
        GET /api/statistics/comparaison_regions/
        """
        if request.user.role != 'SUPER_ADMIN':
            return Response({
                'status': 'error',
                'message': 'Accès réservé aux Super Admins'
            }, status=status.HTTP_403_FORBIDDEN)
        
        regions = Region.objects.all()
        comparaisons = []
        
        for region in regions:
            try:
                data = CacheStatistique.obtenir('REGION', str(region.id), 'GENERAL', auto_refresh=False)
                
                if data:
                    comparaisons.append({
                        'region': region.nom_region,
                        'code': region.code_region,
                        'taux_participation': data.get('taux_participation', 0),
                        'taux_soumission': data.get('taux_soumission', 0),
                        'total_incidents': data.get('incidents', {}).get('total', 0),
                        'candidat_tete': data.get('top_candidats', [{}])[0].get('candidat__nom_complet', 'N/A') if data.get('top_candidats') else 'N/A'
                    })
            except:
                continue
        
        serializer = ComparaisonRegionsSerializer(comparaisons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export des statistiques en différents formats
        GET /api/statistics/export/?format=csv&type=region&region_id=xxx
        """
        format_export = request.query_params.get('format', 'json')
        
        if format_export not in ['json', 'csv', 'excel']:
            return Response({
                'status': 'error',
                'message': 'Format non supporté. Utilisez: json, csv, excel'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Implémenter l'export selon le format
        
        return Response({
            'status': 'not_implemented',
            'message': 'Export à implémenter'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


# ============================================================
# VIEWSETS POUR MODÈLES SPÉCIALISÉS
# ============================================================

class StatistiqueRegionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour StatistiqueRegion"""
    queryset = StatistiqueRegion.objects.select_related('region')
    serializer_class = StatistiqueRegionSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]


class StatistiqueBureauViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour StatistiqueBureau"""
    queryset = StatistiqueBureau.objects.select_related('bureau')
    serializer_class = StatistiqueBureauSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]


class StatistiqueCandidatViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour StatistiqueCandidat"""
    queryset = StatistiqueCandidat.objects.select_related('candidat')
    serializer_class = StatistiqueCandidatSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]
    
    @action(detail=False, methods=['get'])
    def classement(self, request):
        """
        Classement national des candidats
        GET /api/statistics/candidats/classement/
        """
        candidats = self.get_queryset().order_by('-total_voix_national')
        serializer = self.get_serializer(candidats, many=True)
        return Response(serializer.data)


class StatistiqueTimelineViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour StatistiqueTimeline"""
    queryset = StatistiqueTimeline.objects.all()
    serializer_class = StatistiqueTimelineSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]
    filter_backends = [DjangoFilterBackend]
    filterset_class = StatistiqueTimelineFilter


class StatistiquePerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour StatistiquePerformance"""
    queryset = StatistiquePerformance.objects.select_related('user')
    serializer_class = StatistiquePerformanceSerializer
    permission_classes = [IsAuthenticated, CanViewStatistics]
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """
        Classement des utilisateurs par performance
        GET /api/statistics/performance/leaderboard/?role=SUPERVISEUR
        """
        role = request.query_params.get('role')
        queryset = self.get_queryset().order_by('-score_global')
        
        if role:
            queryset = queryset.filter(user__role=role)
        
        # Limiter à top 100
        queryset = queryset[:100]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SnapshotQuotidienViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour SnapshotQuotidien"""
    queryset = SnapshotQuotidien.objects.all()
    serializer_class = SnapshotQuotidienSerializer
    permission_classes = [IsAuthenticated, CanViewNationalStatistics]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SnapshotQuotidienFilter
    
    @action(detail=False, methods=['get'])
    def tendances(self, request):
        """
        Analyse des tendances sur une période
        GET /api/statistics/snapshots/tendances/?jours=30
        """
        jours = int(request.query_params.get('jours', 30))
        date_limite = timezone.now().date() - timedelta(days=jours)
        
        snapshots = self.get_queryset().filter(date__gte=date_limite).order_by('date')
        
        if not snapshots.exists():
            return Response({
                'status': 'error',
                'message': 'Aucun snapshot trouvé pour cette période'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculer les tendances
        premier = snapshots.first()
        dernier = snapshots.last()
        
        tendances = {
            'periode': {
                'debut': premier.date,
                'fin': dernier.date,
                'jours': jours
            },
            'evolution': {
                'pv_soumis': {
                    'debut': premier.total_pv_soumis,
                    'fin': dernier.total_pv_soumis,
                    'variation': dernier.total_pv_soumis - premier.total_pv_soumis,
                    'variation_pct': round(
                        ((dernier.total_pv_soumis - premier.total_pv_soumis) / premier.total_pv_soumis * 100), 2
                    ) if premier.total_pv_soumis > 0 else 0
                },
                'participation': {
                    'debut': premier.taux_participation_global,
                    'fin': dernier.taux_participation_global,
                    'variation': round(dernier.taux_participation_global - premier.taux_participation_global, 2)
                },
                'incidents': {
                    'debut': premier.total_incidents,
                    'fin': dernier.total_incidents,
                    'variation': dernier.total_incidents - premier.total_incidents
                }
            },
            'snapshots': SnapshotQuotidienSerializer(snapshots, many=True).data
        }
        
        return Response(tendances)