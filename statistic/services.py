# statistics/services.py
"""
Service de calcul et gestion des statistiques
"""
from django.db import transaction
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
import time
import logging

from statistic.models import (
    CacheStatistique, StatistiqueRegion, StatistiqueBureau,
    StatistiqueCandidat, StatistiqueTimeline, StatistiquePerformance,
    LogRefreshStatistique
)
from geography.models import Region, BureauVote
from pv.models import ProcesVerbal, Candidat, ResultatCandidat
from incidents.models import Incident
from accounts.models import User

logger = logging.getLogger(__name__)


class StatistiqueService:
    """Service central de gestion des statistiques"""
    
    def __init__(self):
        self.start_time = None
    
    def _start_timer(self):
        """Démarre le chronomètre"""
        self.start_time = time.time()
    
    def _get_duration_ms(self):
        """Retourne la durée en millisecondes"""
        if self.start_time:
            return int((time.time() - self.start_time) * 1000)
        return 0
    
    # ========== CALCUL STATISTIQUES RÉGION ==========
    
    def calculer_stats_region(self, region):
        """Calcule toutes les statistiques d'une région"""
        self._start_timer()
        
        # Statistiques bureaux
        bureaux = BureauVote.objects.par_region(region)
        total_bureaux = bureaux.count()
        total_inscrits = bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        
        # Statistiques PV
        pv_region = ProcesVerbal.objects.par_region(region)
        total_pv = pv_region.count()
        pv_valides = pv_region.filter(statut='VALIDE').count()
        pv_en_attente = pv_region.filter(statut='EN_ATTENTE').count()
        pv_rejetes = pv_region.filter(statut='REJETE').count()
        
        # Statistiques participation
        pv_valides_qs = pv_region.filter(statut='VALIDE')
        participation = pv_valides_qs.aggregate(
            total_votants=Sum('nombre_votants'),
            total_exprimes=Sum('suffrages_exprimes'),
            total_nuls=Sum('bulletins_nuls'),
            total_blancs=Sum('bulletins_blancs')
        )
        
        # Statistiques incidents
        incidents = Incident.objects.par_region(region)
        stats_incidents = {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite__in=['URGENTE', 'CRITIQUE']).count()
        }
        
        # Top 3 candidats
        top_candidats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=region,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')[:3]
        
        data = {
            # Bureaux
            'total_bureaux': total_bureaux,
            'total_inscrits': total_inscrits,
            'moyenne_inscrits': total_inscrits / total_bureaux if total_bureaux > 0 else 0,
            
            # PV
            'total_pv': total_pv,
            'pv_valides': pv_valides,
            'pv_en_attente': pv_en_attente,
            'pv_rejetes': pv_rejetes,
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round((pv_valides / total_pv * 100), 2) if total_pv > 0 else 0,
            
            # Participation
            'total_votants': participation['total_votants'] or 0,
            'total_exprimes': participation['total_exprimes'] or 0,
            'total_nuls': participation['total_nuls'] or 0,
            'total_blancs': participation['total_blancs'] or 0,
            'taux_participation': round(
                (participation['total_votants'] / total_inscrits * 100), 2
            ) if total_inscrits > 0 else 0,
            'taux_nuls': round(
                (participation['total_nuls'] / participation['total_votants'] * 100), 2
            ) if participation['total_votants'] and participation['total_votants'] > 0 else 0,
            
            # Incidents
            'incidents': stats_incidents,
            
            # Résultats
            'top_candidats': list(top_candidats),
            
            # Métadonnées
            'date_calcul': timezone.now().isoformat(),
            'duree_calcul_ms': self._get_duration_ms()
        }
        
        return data
    
    # ========== CALCUL STATISTIQUES BUREAU ==========
    
    def calculer_stats_bureau(self, bureau):
        """Calcule les statistiques d'un bureau"""
        self._start_timer()
        
        # PV du bureau
        pv_valide = bureau.proces_verbaux.filter(statut='VALIDE').first()
        
        data = {
            'has_pv_valide': pv_valide is not None,
            'pv_id': str(pv_valide.id) if pv_valide else None,
            'statut_pv': pv_valide.statut if pv_valide else None,
        }
        
        if pv_valide:
            # Participation
            data.update({
                'nombre_votants': pv_valide.nombre_votants,
                'suffrages_exprimes': pv_valide.suffrages_exprimes,
                'bulletins_nuls': pv_valide.bulletins_nuls,
                'bulletins_blancs': pv_valide.bulletins_blancs,
                'taux_participation': pv_valide.taux_participation,
            })
            
            # Résultats
            resultats = pv_valide.resultats.select_related('candidat').order_by('-nombre_voix')
            data['resultats_candidats'] = [
                {
                    'candidat': r.candidat.nom_complet,
                    'parti': r.candidat.parti_politique,
                    'voix': r.nombre_voix,
                    'pourcentage': r.pourcentage_bureau
                }
                for r in resultats
            ]
            
            if resultats:
                premier = resultats[0]
                data['candidat_vainqueur'] = premier.candidat.nom_complet
                data['voix_vainqueur'] = premier.nombre_voix
        
        # Incidents
        incidents = bureau.incidents.all()
        data['total_incidents'] = incidents.count()
        data['incidents_ouverts'] = incidents.filter(statut='OUVERT').count()
        data['incidents_critiques'] = incidents.filter(priorite='CRITIQUE').count()
        
        # Superviseur
        superviseur = bureau.superviseurs.first()
        if superviseur:
            data['superviseur_nom'] = superviseur.nom_complet
            data['superviseur_id'] = str(superviseur.id)
        
        data['duree_calcul_ms'] = self._get_duration_ms()
        
        return data
    
    # ========== CALCUL STATISTIQUES CANDIDAT ==========
    
    def calculer_stats_candidat(self, candidat):
        """Calcule les statistiques d'un candidat"""
        self._start_timer()
        
        # Résultats nationaux
        resultats = ResultatCandidat.objects.filter(
            candidat=candidat,
            proces_verbal__statut='VALIDE'
        ).aggregate(
            total_voix=Sum('nombre_voix'),
            nb_bureaux=Count('proces_verbal', distinct=True)
        )
        
        # Total national tous candidats
        total_national = ResultatCandidat.objects.filter(
            proces_verbal__statut='VALIDE'
        ).aggregate(Sum('nombre_voix'))['nombre_voix__sum'] or 1
        
        data = {
            'total_voix_national': resultats['total_voix'] or 0,
            'nombre_bureaux': resultats['nb_bureaux'] or 0,
            'pourcentage_national': round(
                (resultats['total_voix'] or 0) / total_national * 100, 2
            ),
        }
        
        # Résultats par région
        resultats_regions = []
        for region in Region.objects.all():
            voix_region = ResultatCandidat.objects.filter(
                candidat=candidat,
                proces_verbal__statut='VALIDE',
                proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=region
            ).aggregate(Sum('nombre_voix'))['nombre_voix__sum'] or 0
            
            if voix_region > 0:
                resultats_regions.append({
                    'region': region.nom_region,
                    'code': region.code_region,
                    'voix': voix_region
                })
        
        data['resultats_par_region'] = sorted(
            resultats_regions, key=lambda x: x['voix'], reverse=True
        )
        
        # Meilleurs bureaux
        meilleurs = ResultatCandidat.objects.filter(
            candidat=candidat,
            proces_verbal__statut='VALIDE'
        ).select_related(
            'proces_verbal__bureau_vote'
        ).order_by('-nombre_voix')[:10]
        
        data['meilleurs_bureaux'] = [
            {
                'bureau': r.proces_verbal.bureau_vote.code_bv,
                'voix': r.nombre_voix,
                'pourcentage': r.pourcentage_bureau
            }
            for r in meilleurs
        ]
        
        data['duree_calcul_ms'] = self._get_duration_ms()
        
        return data
    
    # ========== CALCUL TIMELINE ==========
    
    def calculer_timeline_soumissions_pv(self, date_debut, date_fin, region=None):
        """Calcule la timeline des soumissions de PV"""
        self._start_timer()
        
        qs = ProcesVerbal.objects.filter(
            date_soumission__gte=date_debut,
            date_soumission__lte=date_fin
        )
        
        if region:
            qs = qs.filter(
                bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=region
            )
        
        # Grouper par heure
        from django.db.models.functions import TruncHour
        
        timeline = qs.annotate(
            heure=TruncHour('date_soumission')
        ).values('heure').annotate(
            count=Count('id')
        ).order_by('heure')
        
        data_points = [
            {
                'date': point['heure'].isoformat(),
                'valeur': point['count']
            }
            for point in timeline
        ]
        
        total = sum(p['valeur'] for p in data_points)
        moyenne = total / len(data_points) if data_points else 0
        
        data = {
            'data_points': data_points,
            'total': total,
            'moyenne': round(moyenne, 2),
            'minimum': min([p['valeur'] for p in data_points]) if data_points else 0,
            'maximum': max([p['valeur'] for p in data_points]) if data_points else 0,
            'duree_calcul_ms': self._get_duration_ms()
        }
        
        return data
    
    # ========== SAUVEGARDE DANS LE CACHE ==========
    
    @transaction.atomic
    def calculer_et_sauvegarder(self, type_entite, entite_id, type_statistique, user=None):
        """
        Calcule les statistiques et les sauvegarde dans le cache
        """
        try:
            # Déterminer la méthode de calcul
            if type_entite == 'REGION' and type_statistique == 'GENERAL':
                region = Region.objects.get(id=entite_id)
                data = self.calculer_stats_region(region)
            
            elif type_entite == 'BUREAU_VOTE' and type_statistique == 'GENERAL':
                bureau = BureauVote.objects.get(id=entite_id)
                data = self.calculer_stats_bureau(bureau)
            
            elif type_entite == 'CANDIDAT' and type_statistique == 'RESULTATS':
                candidat = Candidat.objects.get(id=entite_id)
                data = self.calculer_stats_candidat(candidat)
            
            else:
                raise ValueError(f"Type non supporté: {type_entite}/{type_statistique}")
            
            # Sauvegarder dans le cache
            cache_obj, created = CacheStatistique.objects.update_or_create(
                type_entite=type_entite,
                entite_id=str(entite_id),
                type_statistique=type_statistique,
                defaults={
                    'data': data,
                    'duree_calcul_ms': data.get('duree_calcul_ms', 0),
                    'is_valid': True,
                    'force_refresh': False,
                    'version': F('version') + 1
                }
            )
            
            # Logger le succès
            LogRefreshStatistique.objects.create(
                cache_statistique=cache_obj,
                cache_key=cache_obj.cache_key,
                type_entite=type_entite,
                type_statistique=type_statistique,
                statut='SUCCESS',
                duree_ms=data.get('duree_calcul_ms', 0),
                triggered_by='service',
                user=user
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur calcul stats {type_entite}/{entite_id}: {str(e)}")
            
            # Logger l'erreur
            LogRefreshStatistique.objects.create(
                cache_key=f"{type_entite}_{entite_id}_{type_statistique}",
                type_entite=type_entite,
                type_statistique=type_statistique,
                statut='ERROR',
                message=str(e),
                duree_ms=self._get_duration_ms(),
                triggered_by='service',
                user=user
            )
            
            raise
    
    # ========== RAFRAÎCHISSEMENT EN MASSE ==========
    
    def rafraichir_tous_les_caches_expires(self):
        """Rafraîchit tous les caches expirés"""
        caches_expires = CacheStatistique.objects.a_rafraichir()
        
        resultats = {
            'total': caches_expires.count(),
            'succes': 0,
            'erreurs': 0
        }
        
        for cache in caches_expires[:100]:  # Limiter à 100 par exécution
            try:
                self.calculer_et_sauvegarder(
                    cache.type_entite,
                    cache.entite_id,
                    cache.type_statistique
                )
                resultats['succes'] += 1
            except Exception as e:
                logger.error(f"Erreur refresh {cache.cache_key}: {str(e)}")
                resultats['erreurs'] += 1
        
        return resultats
    
    # ========== SNAPSHOT NATIONAL ==========
    
    def calculer_snapshot_national(self):
        """Calcule le snapshot national du jour"""
        # Statistiques globales
        total_bureaux = BureauVote.objects.actifs().count()
        total_inscrits = BureauVote.objects.aggregate(
            Sum('nombre_inscrits')
        )['nombre_inscrits__sum'] or 0
        
        # PV
        total_pv = ProcesVerbal.objects.count()
        pv_valides = ProcesVerbal.objects.valides().count()
        
        # Participation
        pv_valides_qs = ProcesVerbal.objects.valides()
        participation = pv_valides_qs.aggregate(
            total_votants=Sum('nombre_votants')
        )
        
        # Incidents
        total_incidents = Incident.objects.count()
        incidents_actifs = Incident.objects.actifs().count()
        incidents_clos = Incident.objects.clos().count()
        
        # Top 3 candidats
        top_3 = ResultatCandidat.objects.filter(
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet'
        ).annotate(
            total=Sum('nombre_voix')
        ).order_by('-total')[:3]
        
        return {
            'total_bureaux': total_bureaux,
            'total_inscrits': total_inscrits,
            'total_pv_soumis': total_pv,
            'total_pv_valides': pv_valides,
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round((pv_valides / total_pv * 100), 2) if total_pv > 0 else 0,
            'total_votants': participation['total_votants'] or 0,
            'taux_participation_global': round(
                (participation['total_votants'] / total_inscrits * 100), 2
            ) if total_inscrits > 0 else 0,
            'total_incidents': total_incidents,
            'incidents_actifs': incidents_actifs,
            'taux_resolution': round(
                (incidents_clos / total_incidents * 100), 2
            ) if total_incidents > 0 else 0,
            'resultats_snapshot': list(top_3)
        }