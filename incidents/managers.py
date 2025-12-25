# apps/incidents/managers.py
from django.db import models
from django.db.models import Count, Avg, Q, F, DurationField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta


class IncidentQuerySet(models.QuerySet):
    """QuerySet personnalisé pour Incident"""
    
    def ouverts(self):
        """Incidents ouverts"""
        return self.filter(statut='OUVERT')
    
    def en_cours(self):
        """Incidents en cours de traitement"""
        return self.filter(statut='EN_COURS')
    
    def traites(self):
        """Incidents traités"""
        return self.filter(statut='TRAITE')
    
    def clos(self):
        """Incidents clos"""
        return self.filter(statut='CLOS')
    
    def actifs(self):
        """Incidents ouverts ou en cours"""
        return self.filter(statut__in=['OUVERT', 'EN_COURS'])
    
    def priorite_haute(self):
        """Incidents de haute priorité"""
        return self.filter(priorite__in=['HAUTE', 'URGENTE', 'CRITIQUE'])
    
    def en_retard(self):
        """Incidents en retard (SLA dépassé)"""
        return self.filter(sla_respecte=False, statut__in=['OUVERT', 'EN_COURS'])
    
    def escalades(self):
        """Incidents escaladés"""
        return self.filter(est_escalade=True)
    
    def par_categorie(self, categorie):
        """Filtre par catégorie"""
        return self.filter(categorie=categorie)
    
    def par_bureau(self, bureau_vote):
        """Filtre par bureau"""
        return self.filter(bureau_vote=bureau_vote)
    
    def par_superviseur(self, superviseur):
        """Filtre par superviseur"""
        return self.filter(superviseur=superviseur)
    
    def par_admin(self, admin):
        """Filtre par admin responsable"""
        return self.filter(admin_responsable=admin)
    
    def par_region(self, region):
        """Filtre par région"""
        return self.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=region
        )
    
    def derniers_jours(self, jours=7):
        """Incidents des derniers jours"""
        date_limite = timezone.now() - timedelta(days=jours)
        return self.filter(created_at__gte=date_limite)
    
    def non_attribues(self):
        """Incidents non attribués"""
        return self.filter(admin_responsable__isnull=True)
    
    def avec_delais(self):
        """Ajoute les délais calculés"""
        return self.annotate(
            temps_ouvert=ExpressionWrapper(
                timezone.now() - F('created_at'),
                output_field=DurationField()
            )
        )
    
    def avec_stats(self):
        """Ajoute les statistiques"""
        return self.annotate(
            nb_messages=Count('messages'),
            nb_photos=Count('photos')
        )


class IncidentManager(models.Manager):
    """Manager personnalisé pour Incident"""
    
    def get_queryset(self):
        return IncidentQuerySet(self.model, using=self._db)
    
    def ouverts(self):
        return self.get_queryset().ouverts()
    
    def actifs(self):
        return self.get_queryset().actifs()
    
    def en_retard(self):
        return self.get_queryset().en_retard()
    
    def priorite_haute(self):
        return self.get_queryset().priorite_haute()
    
    def avec_stats(self):
        return self.get_queryset().avec_stats()
    
    