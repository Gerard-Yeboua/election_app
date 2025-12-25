# statistic/services/statistique_service.py
from django.db.models import Count, Sum, Avg, Q, F
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from pv.models import ProcesVerbal, ResultatCandidat
from incidents.models import Incident
from geography.models import BureauVote, Region


class StatistiqueService:
    """Service de calcul et mise en cache des statistiques"""
    
    def get_stats_region(self, region, force_refresh=False):
        """Obtenir les statistiques d'une région"""
        cache_key = f'stats_region_{region.id}'
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        bureaux = BureauVote.objects.filter(region=region)
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__region=region,
            statut='VALIDE'
        )
        
        stats = {
            'total_bureaux': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'pv_valides': pv_valides.count(),
            'pv_en_attente': ProcesVerbal.objects.filter(
                bureau_vote__region=region,
                statut='EN_ATTENTE'
            ).count(),
            'pv_rejetes': ProcesVerbal.objects.filter(
                bureau_vote__region=region,
                statut='REJETE'
            ).count(),
            'taux_soumission': 0,
            'total_votants': pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0,
            'taux_participation': 0,
            'total_incidents': Incident.objects.filter(bureau_vote__region=region).count(),
        }
        
        if stats['total_bureaux'] > 0:
            stats['taux_soumission'] = (pv_valides.count() / stats['total_bureaux'] * 100)
        
        if stats['total_inscrits'] > 0:
            stats['taux_participation'] = (stats['total_votants'] / stats['total_inscrits'] * 100)
        
        cache.set(cache_key, stats, 300)  # Cache 5 minutes
        return stats
    
    def get_stats_national(self, force_refresh=False):
        """Obtenir les statistiques nationales"""
        cache_key = 'stats_national'
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        bureaux = BureauVote.objects.all()
        pv_valides = ProcesVerbal.objects.filter(statut='VALIDE')
        
        stats = {
            'total_bureaux': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'pv_valides': pv_valides.count(),
            'pv_en_attente': ProcesVerbal.objects.filter(statut='EN_ATTENTE').count(),
            'pv_rejetes': ProcesVerbal.objects.filter(statut='REJETE').count(),
            'taux_soumission': 0,
            'total_votants': pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0,
            'taux_participation': 0,
            'total_incidents': Incident.objects.count(),
        }
        
        if stats['total_bureaux'] > 0:
            stats['taux_soumission'] = (pv_valides.count() / stats['total_bureaux'] * 100)
        
        if stats['total_inscrits'] > 0:
            stats['taux_participation'] = (stats['total_votants'] / stats['total_inscrits'] * 100)
        
        cache.set(cache_key, stats, 300)
        return stats
    
    def get_stats_bureau(self, bureau, force_refresh=False):
        """Obtenir les statistiques d'un bureau"""
        cache_key = f'stats_bureau_{bureau.id}'
        
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        pv_valide = ProcesVerbal.objects.filter(
            bureau_vote=bureau,
            statut='VALIDE'
        ).first()
        
        stats = {
            'has_pv_valide': pv_valide is not None,
            'nombre_votants': pv_valide.nombre_votants if pv_valide else 0,
            'taux_participation': pv_valide.taux_participation if pv_valide else 0,
            'total_incidents': Incident.objects.filter(bureau_vote=bureau).count()
        }
        
        cache.set(cache_key, stats, 300)
        return stats
    
    def get_top_candidats(self, limit=5, region=None):
        """Obtenir le top des candidats"""
        resultats = ResultatCandidat.objects.filter(
            pv__statut='VALIDE'
        )
        
        if region:
            resultats = resultats.filter(pv__bureau_vote__region=region)
        
        top = resultats.values(
            'candidat__id',
            'candidat__nom_complet',
            'candidat__parti_politique'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')[:limit]
        
        return list(top)
    
    def get_evolution_soumissions(self, jours=7):
        """Obtenir l'évolution des soumissions sur N jours"""
        cache_key = f'evolution_soumissions_{jours}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        date_debut = timezone.now() - timedelta(days=jours)
        
        evolution = []
        for i in range(jours):
            date = date_debut + timedelta(days=i)
            date_fin = date + timedelta(days=1)
            
            count = ProcesVerbal.objects.filter(
                date_soumission__gte=date,
                date_soumission__lt=date_fin
            ).count()
            
            evolution.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })
        
        cache.set(cache_key, evolution, 600)  # 10 minutes
        return evolution
    
    def calculer_et_sauvegarder(self, type_entite, entite_id):
        """Calculer et sauvegarder les statistiques"""
        if type_entite == 'region':
            from apps.geography.models import Region
            region = Region.objects.get(id=entite_id)
            return self.get_stats_region(region, force_refresh=True)
        elif type_entite == 'national':
            return self.get_stats_national(force_refresh=True)
        elif type_entite == 'bureau':
            from apps.geography.models import BureauVote
            bureau = BureauVote.objects.get(id=entite_id)
            return self.get_stats_bureau(bureau, force_refresh=True)
    
    def invalidate_cache_region(self, region):
        """Invalider le cache d'une région"""
        cache.delete(f'stats_region_{region.id}')
        cache.delete('stats_national')
    
    def invalidate_cache_bureau(self, bureau):
        """Invalider le cache d'un bureau"""
        cache.delete(f'stats_bureau_{bureau.id}')
        if bureau.region:
            self.invalidate_cache_region(bureau.region)
    
    def get_comparaison_regions(self):
        """Comparer les performances des régions"""
        cache_key = 'comparaison_regions'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        regions = Region.objects.all()
        comparaison = []
        
        for region in regions:
            stats = self.get_stats_region(region)
            comparaison.append({
                'region': region.nom_region,
                'region_id': region.id,
                'total_bureaux': stats['total_bureaux'],
                'pv_valides': stats['pv_valides'],
                'taux_soumission': stats['taux_soumission'],
                'taux_participation': stats['taux_participation'],
            })
        
        cache.set(cache_key, comparaison, 300)
        return comparaison


# Instance singleton
statistique_service = StatistiqueService()