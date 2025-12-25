# statistic/managers.py
from django.db import models
from django.utils import timezone
from datetime import timedelta


class CacheStatistiqueManager(models.Manager):
    """Manager pour CacheStatistique"""
    
    def valides(self):
        """Retourne les caches valides"""
        return self.filter(
            is_valid=True,
            date_expiration__gt=timezone.now(),
            force_refresh=False
        )
    
    def expires(self):
        """Retourne les caches expirés"""
        return self.filter(
            models.Q(date_expiration__lte=timezone.now()) |
            models.Q(is_valid=False) |
            models.Q(force_refresh=True)
        )
    
    def par_type(self, type_entite, type_statistique):
        """Filtre par type d'entité et type de statistique"""
        return self.filter(
            type_entite=type_entite,
            type_statistique=type_statistique
        )
    
    def a_rafraichir(self):
        """Retourne les caches à rafraîchir"""
        return self.expires().order_by('-hit_count')
    
    def peu_utilises(self, jours=7):
        """Caches peu utilisés dans les X derniers jours"""
        limite = timezone.now() - timedelta(days=jours)
        return self.filter(
            models.Q(last_accessed__lt=limite) |
            models.Q(last_accessed__isnull=True)
        )


class StatistiqueTimelineManager(models.Manager):
    """Manager pour StatistiqueTimeline"""
    
    def pour_periode(self, date_debut, date_fin):
        """Timeline pour une période donnée"""
        return self.filter(
            date_debut__gte=date_debut,
            date_fin__lte=date_fin
        )
    
    def par_region(self, region):
        """Timeline pour une région"""
        return self.filter(region=region)
    
    def par_type(self, type_timeline):
        """Timeline par type"""
        return self.filter(type_timeline=type_timeline)