# apps/geography/managers.py
from django.db import models
from django.db.models import Count, Sum, Avg, Q


class BureauVoteQuerySet(models.QuerySet):
    """QuerySet personnalisé pour BureauVote"""
    
    def actifs(self):
        """Retourne les bureaux actifs"""
        return self.filter(est_actif=True)
    
    def par_region(self, region):
        """Filtre par région"""
        return self.filter(
            lieu_vote__sous_prefecture__commune__departement__region=region
        )
    
    def par_departement(self, departement):
        """Filtre par département"""
        return self.filter(
            lieu_vote__sous_prefecture__commune__departement=departement
        )
    
    def par_commune(self, commune):
        """Filtre par commune"""
        return self.filter(lieu_vote__sous_prefecture__commune=commune)
    
    def avec_pv_valide(self):
        """Bureaux ayant un PV validé"""
        return self.filter(proces_verbaux__statut='VALIDE').distinct()
    
    def sans_pv(self):
        """Bureaux sans aucun PV"""
        return self.filter(proces_verbaux__isnull=True)
    
    def avec_incidents_ouverts(self):
        """Bureaux ayant des incidents ouverts"""
        return self.filter(
            incidents__statut__in=['OUVERT', 'EN_COURS']
        ).distinct()
    
    def avec_stats(self):
        """Ajoute les statistiques agrégées"""
        return self.annotate(
            nb_pv=Count('proces_verbaux'),
            nb_pv_valides=Count('proces_verbaux', filter=Q(proces_verbaux__statut='VALIDE')),
            nb_incidents=Count('incidents'),
            nb_incidents_ouverts=Count('incidents', filter=Q(incidents__statut='OUVERT'))
        )


class BureauVoteManager(models.Manager):
    """Manager personnalisé pour BureauVote"""
    
    def get_queryset(self):
        return BureauVoteQuerySet(self.model, using=self._db)
    
    def actifs(self):
        return self.get_queryset().actifs()
    
    def par_region(self, region):
        return self.get_queryset().par_region(region)
    
    def avec_stats(self):
        return self.get_queryset().avec_stats()
    