from django.db import models

# Create your models here.
# /statistics/models.py
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Sum, Count, Avg, Q, F
import uuid
from datetime import timedelta
import json

from statistic.managers import CacheStatistiqueManager, StatistiqueTimelineManager


# ============================================================
# MODÈLE CACHE STATISTIQUES PRINCIPAL
# ============================================================

class CacheStatistique(models.Model):
    """
    Modèle principal de cache pour toutes les statistiques
    Système générique avec TTL et invalidation intelligente
    """
    
    TYPE_ENTITE_CHOICES = [
        ('NATIONAL', 'National'),
        ('REGION', 'Région'),
        ('DEPARTEMENT', 'Département'),
        ('COMMUNE', 'Commune'),
        ('SOUS_PREFECTURE', 'Sous-préfecture'),
        ('LIEU_VOTE', 'Lieu de vote'),
        ('BUREAU_VOTE', 'Bureau de vote'),
        ('CANDIDAT', 'Candidat'),
        ('USER', 'Utilisateur'),
    ]
    
    TYPE_STATISTIQUE_CHOICES = [
        ('GENERAL', 'Statistiques générales'),
        ('PV', 'Statistiques PV'),
        ('PARTICIPATION', 'Statistiques participation'),
        ('INCIDENTS', 'Statistiques incidents'),
        ('RESULTATS', 'Résultats électoraux'),
        ('PERFORMANCE', 'Performance utilisateurs'),
        ('TIMELINE', 'Évolution temporelle'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identification du cache
    type_entite = models.CharField(
        max_length=20,
        choices=TYPE_ENTITE_CHOICES,
        help_text="Type d'entité concernée"
    )
    
    entite_id = models.CharField(
        max_length=100,
        help_text="ID de l'entité (UUID, code, 'national', etc.)",
        db_index=True
    )
    
    type_statistique = models.CharField(
        max_length=20,
        choices=TYPE_STATISTIQUE_CHOICES,
        help_text="Type de statistique"
    )
    
    # Clé unique pour accès rapide
    cache_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Clé unique: {type_entite}_{entite_id}_{type_statistique}"
    )
    
    # Données
    data = models.JSONField(
        default=dict,
        help_text="Données statistiques en JSON"
    )
    
    # Métadonnées du cache
    date_calcul = models.DateTimeField(
        auto_now=True,
        help_text="Date du dernier calcul"
    )
    
    duree_calcul_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Durée du calcul en millisecondes"
    )
    
    ttl_minutes = models.IntegerField(
        default=60,
        help_text="Time To Live en minutes (durée de validité)"
    )
    
    date_expiration = models.DateTimeField(
        db_index=True,
        help_text="Date d'expiration du cache"
    )
    
    # Flags de gestion
    is_valid = models.BooleanField(
        default=True,
        help_text="False si le cache est invalidé"
    )
    
    force_refresh = models.BooleanField(
        default=False,
        help_text="True pour forcer le rafraîchissement au prochain accès"
    )
    
    # Compteurs
    hit_count = models.IntegerField(
        default=0,
        help_text="Nombre d'accès au cache"
    )
    
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date du dernier accès"
    )
    
    # Version pour gestion de concurrence
    version = models.IntegerField(
        default=1,
        help_text="Version du cache (incrémenté à chaque recalcul)"
    )
    objects = CacheStatistiqueManager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cache_statistiques'
        verbose_name = 'Cache statistique'
        verbose_name_plural = 'Caches statistiques'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['type_entite', 'entite_id']),
            models.Index(fields=['type_statistique']),
            models.Index(fields=['date_expiration', 'is_valid']),
            models.Index(fields=['is_valid', 'force_refresh']),
        ]
        unique_together = ['type_entite', 'entite_id', 'type_statistique']
    
    def __str__(self):
        return f"{self.cache_key} (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Générer la clé de cache si nécessaire
        if not self.cache_key:
            self.cache_key = self.generer_cache_key()
        
        # Calculer la date d'expiration
        self.date_expiration = timezone.now() + timedelta(minutes=self.ttl_minutes)
        
        super().save(*args, **kwargs)
    
    def generer_cache_key(self):
        """Génère une clé de cache unique"""
        return f"{self.type_entite}_{self.entite_id}_{self.type_statistique}".lower()
    
    @property
    def est_expire(self):
        """Vérifie si le cache est expiré"""
        return timezone.now() > self.date_expiration
    
    @property
    def est_valide(self):
        """Vérifie si le cache est valide (non expiré et non invalidé)"""
        return self.is_valid and not self.est_expire and not self.force_refresh
    
    def invalider(self):
        """Invalide le cache"""
        self.is_valid = False
        self.save(update_fields=['is_valid'])
    
    def forcer_refresh(self):
        """Force le rafraîchissement au prochain accès"""
        self.force_refresh = True
        self.save(update_fields=['force_refresh'])
    
    def incrementer_hit(self):
        """Incrémente le compteur d'accès"""
        self.hit_count = F('hit_count') + 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['hit_count', 'last_accessed'])
    
    @classmethod
    def obtenir(cls, type_entite, entite_id, type_statistique, auto_refresh=True):
        """
        Obtient les statistiques depuis le cache
        Rafraîchit automatiquement si nécessaire
        """
        cache_key = f"{type_entite}_{entite_id}_{type_statistique}".lower()
        
        try:
            cache_obj = cls.objects.get(cache_key=cache_key)
            
            # Vérifier la validité
            if cache_obj.est_valide:
                cache_obj.incrementer_hit()
                return cache_obj.data
            
            # Cache invalide - rafraîchir si auto_refresh
            if auto_refresh:
                from statistic.services import StatistiqueService
                service = StatistiqueService()
                return service.calculer_et_sauvegarder(
                    type_entite, entite_id, type_statistique
                )
            
            return None
            
        except cls.DoesNotExist:
            # Cache n'existe pas - créer si auto_refresh
            if auto_refresh:
                from statistic.services import StatistiqueService
                service = StatistiqueService()
                return service.calculer_et_sauvegarder(
                    type_entite, entite_id, type_statistique
                )
            
            return None
    
    @classmethod
    def invalider_par_pattern(cls, pattern):
        """Invalide tous les caches correspondant à un pattern"""
        cls.objects.filter(cache_key__contains=pattern).update(
            is_valid=False,
            force_refresh=True
        )
    
    @classmethod
    def nettoyer_expires(cls):
        """Supprime les caches expirés depuis plus de 7 jours"""
        limite = timezone.now() - timedelta(days=7)
        cls.objects.filter(
            date_expiration__lt=limite,
            is_valid=False
        ).delete()


# ============================================================
# MODÈLES SPÉCIALISÉS DE STATISTIQUES
# ============================================================

class StatistiqueRegion(models.Model):
    """
    Cache optimisé pour les statistiques régionales
    Pré-calculées et dénormalisées pour performance maximale
    """
    
    region = models.OneToOneField(
        'geography.Region',
        on_delete=models.CASCADE,
        related_name='statistiques'
    )
    
    # Statistiques bureaux
    total_bureaux = models.IntegerField(default=0)
    total_inscrits = models.IntegerField(default=0)
    moyenne_inscrits_par_bureau = models.FloatField(default=0)
    
    # Statistiques PV
    total_pv_soumis = models.IntegerField(default=0)
    total_pv_valides = models.IntegerField(default=0)
    total_pv_en_attente = models.IntegerField(default=0)
    total_pv_rejetes = models.IntegerField(default=0)
    taux_soumission = models.FloatField(default=0)
    taux_validation = models.FloatField(default=0)
    
    # Statistiques participation
    total_votants = models.IntegerField(default=0)
    total_suffrages_exprimes = models.IntegerField(default=0)
    total_bulletins_nuls = models.IntegerField(default=0)
    total_bulletins_blancs = models.IntegerField(default=0)
    taux_participation = models.FloatField(default=0)
    taux_nuls = models.FloatField(default=0)
    taux_blancs = models.FloatField(default=0)
    
    # Statistiques incidents
    total_incidents = models.IntegerField(default=0)
    incidents_ouverts = models.IntegerField(default=0)
    incidents_en_cours = models.IntegerField(default=0)
    incidents_traites = models.IntegerField(default=0)
    incidents_clos = models.IntegerField(default=0)
    incidents_urgents = models.IntegerField(default=0)
    taux_resolution_incidents = models.FloatField(default=0)
    delai_moyen_resolution_incidents = models.FloatField(null=True, blank=True)
    
    # Top 3 résultats (JSON)
    top_3_candidats = models.JSONField(
        default=list,
        help_text="Top 3 des candidats avec leurs scores"
    )
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'statistiques_regions'
        verbose_name = 'Statistique région'
        verbose_name_plural = 'Statistiques régions'
    
    def __str__(self):
        return f"Stats {self.region.nom_region}"


class StatistiqueBureau(models.Model):
    """
    Cache pour les statistiques d'un bureau de vote
    """
    
    bureau = models.OneToOneField(
        'geography.BureauVote',
        on_delete=models.CASCADE,
        related_name='statistiques'
    )
    
    # PV
    has_pv_valide = models.BooleanField(default=False)
    pv_id = models.UUIDField(null=True, blank=True)
    statut_pv = models.CharField(max_length=20, blank=True, null=True)
    date_soumission_pv = models.DateTimeField(null=True, blank=True)
    date_validation_pv = models.DateTimeField(null=True, blank=True)
    
    # Participation
    nombre_votants = models.IntegerField(default=0)
    suffrages_exprimes = models.IntegerField(default=0)
    bulletins_nuls = models.IntegerField(default=0)
    bulletins_blancs = models.IntegerField(default=0)
    taux_participation = models.FloatField(default=0)
    
    # Résultats
    resultats_candidats = models.JSONField(
        default=list,
        help_text="Liste des résultats par candidat"
    )
    
    candidat_vainqueur = models.CharField(max_length=200, blank=True, null=True)
    voix_vainqueur = models.IntegerField(default=0)
    
    # Incidents
    total_incidents = models.IntegerField(default=0)
    incidents_ouverts = models.IntegerField(default=0)
    incidents_critiques = models.IntegerField(default=0)
    
    # Superviseur
    superviseur_nom = models.CharField(max_length=200, blank=True, null=True)
    superviseur_id = models.UUIDField(null=True, blank=True)
    derniere_activite = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'statistiques_bureaux'
        verbose_name = 'Statistique bureau'
        verbose_name_plural = 'Statistiques bureaux'
    
    def __str__(self):
        return f"Stats {self.bureau.code_bv}"


class StatistiqueCandidat(models.Model):
    """
    Cache pour les statistiques d'un candidat
    """
    
    candidat = models.OneToOneField(
        'pv.Candidat',
        on_delete=models.CASCADE,
        related_name='statistiques'
    )
    
    # Résultats nationaux
    total_voix_national = models.IntegerField(default=0)
    nombre_bureaux = models.IntegerField(default=0)
    pourcentage_national = models.FloatField(default=0)
    position_nationale = models.IntegerField(null=True, blank=True)
    
    # Détails par région
    resultats_par_region = models.JSONField(
        default=list,
        help_text="Résultats détaillés par région"
    )
    
    # Meilleures performances
    meilleurs_bureaux = models.JSONField(
        default=list,
        help_text="Top 10 bureaux avec les meilleurs scores"
    )
    
    # Statistiques avancées
    moyenne_voix_par_bureau = models.FloatField(default=0)
    ecart_type = models.FloatField(null=True, blank=True)
    score_minimum = models.IntegerField(default=0)
    score_maximum = models.IntegerField(default=0)
    
    # Tendances
    evolution_7_jours = models.JSONField(
        default=list,
        help_text="Évolution des voix sur 7 jours"
    )
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'statistiques_candidats'
        verbose_name = 'Statistique candidat'
        verbose_name_plural = 'Statistiques candidats'
    
    def __str__(self):
        return f"Stats {self.candidat.nom_complet}"


class StatistiqueTimeline(models.Model):
    """
    Cache pour les statistiques temporelles (évolution)
    """
    
    TYPE_CHOICES = [
        ('PV_SOUMISSIONS', 'Soumissions de PV'),
        ('PV_VALIDATIONS', 'Validations de PV'),
        ('INCIDENTS', 'Incidents'),
        ('PARTICIPATION', 'Participation'),
        ('RESULTATS', 'Résultats'),
    ]
    
    GRANULARITE_CHOICES = [
        ('HEURE', 'Par heure'),
        ('JOUR', 'Par jour'),
        ('SEMAINE', 'Par semaine'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identification
    type_timeline = models.CharField(max_length=20, choices=TYPE_CHOICES)
    granularite = models.CharField(max_length=20, choices=GRANULARITE_CHOICES)
    
    # Périmètre (optionnel)
    region = models.ForeignKey(
        'geography.Region',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Période
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    
    # Données temporelles
    data_points = models.JSONField(
        default=list,
        help_text="Liste des points de données [{date, valeur}, ...]"
    )
    objects = StatistiqueTimelineManager()
    # Statistiques agrégées
    total = models.IntegerField(default=0)
    moyenne = models.FloatField(default=0)
    minimum = models.IntegerField(default=0)
    maximum = models.IntegerField(default=0)
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'statistiques_timeline'
        verbose_name = 'Statistique timeline'
        verbose_name_plural = 'Statistiques timeline'
        indexes = [
            models.Index(fields=['type_timeline', 'granularite']),
            models.Index(fields=['date_debut', 'date_fin']),
            models.Index(fields=['region']),
        ]
    
    def __str__(self):
        return f"{self.type_timeline} - {self.granularite}"


class StatistiquePerformance(models.Model):
    """
    Cache pour les statistiques de performance des utilisateurs
    """
    
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='statistiques_performance'
    )
    
    # Pour les superviseurs
    total_pv_soumis = models.IntegerField(default=0)
    pv_valides = models.IntegerField(default=0)
    pv_rejetes = models.IntegerField(default=0)
    taux_validation = models.FloatField(default=0)
    delai_moyen_soumission = models.FloatField(null=True, blank=True)
    
    incidents_signales = models.IntegerField(default=0)
    incidents_critiques = models.IntegerField(default=0)
    
    total_checkins = models.IntegerField(default=0)
    duree_moyenne_presence = models.FloatField(null=True, blank=True)
    
    # Pour les admins
    pv_valides_admin = models.IntegerField(default=0)
    pv_rejetes_admin = models.IntegerField(default=0)
    delai_moyen_validation = models.FloatField(null=True, blank=True)
    
    incidents_traites = models.IntegerField(default=0)
    incidents_resolus = models.IntegerField(default=0)
    taux_resolution_incidents = models.FloatField(default=0)
    delai_moyen_resolution = models.FloatField(null=True, blank=True)
    
    # Scores
    score_reactivite = models.FloatField(default=0)
    score_qualite = models.FloatField(default=0)
    score_global = models.FloatField(default=0)
    
    # Classement
    rang_national = models.IntegerField(null=True, blank=True)
    rang_regional = models.IntegerField(null=True, blank=True)
    
    # Métadonnées
    date_calcul = models.DateTimeField(auto_now=True)
    version = models.IntegerField(default=1)
    
    class Meta:
        db_table = 'statistiques_performance'
        verbose_name = 'Statistique performance'
        verbose_name_plural = 'Statistiques performance'
        ordering = ['-score_global']
    
    def __str__(self):
        return f"Performance {self.user.nom_complet}"


# ============================================================
# MODÈLE LOG DE RAFRAÎCHISSEMENT
# ============================================================

class LogRefreshStatistique(models.Model):
    """
    Historique des rafraîchissements de cache
    Permet de tracer les performances et détecter les problèmes
    """
    
    STATUT_CHOICES = [
        ('SUCCESS', 'Succès'),
        ('ERROR', 'Erreur'),
        ('TIMEOUT', 'Timeout'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    cache_statistique = models.ForeignKey(
        CacheStatistique,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_refresh'
    )
    
    # Identification
    cache_key = models.CharField(max_length=255)
    type_entite = models.CharField(max_length=20)
    type_statistique = models.CharField(max_length=20)
    
    # Résultat
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES)
    message = models.TextField(blank=True, null=True)
    
    # Performance
    duree_ms = models.IntegerField(help_text="Durée en millisecondes")
    nombre_requetes_db = models.IntegerField(default=0)
    
    # Contexte
    triggered_by = models.CharField(
        max_length=50,
        help_text="Ce qui a déclenché le refresh (auto, manual, api, etc.)"
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Métadonnées
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'logs_refresh_statistiques'
        verbose_name = 'Log refresh statistique'
        verbose_name_plural = 'Logs refresh statistiques'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['cache_key', 'timestamp']),
            models.Index(fields=['statut', 'timestamp']),
            models.Index(fields=['duree_ms']),
        ]
    
    def __str__(self):
        return f"{self.cache_key} - {self.statut} ({self.duree_ms}ms)"


# ============================================================
# MODÈLE SNAPSHOT QUOTIDIEN
# ============================================================

class SnapshotQuotidien(models.Model):
    """
    Snapshot des statistiques principales chaque jour
    Permet d'analyser les tendances historiques
    """
    
    date = models.DateField(unique=True, db_index=True)
    
    # Statistiques globales
    total_bureaux = models.IntegerField(default=0)
    total_inscrits = models.IntegerField(default=0)
    
    # PV
    total_pv_soumis = models.IntegerField(default=0)
    total_pv_valides = models.IntegerField(default=0)
    taux_soumission = models.FloatField(default=0)
    taux_validation = models.FloatField(default=0)
    
    # Participation
    total_votants = models.IntegerField(default=0)
    taux_participation_global = models.FloatField(default=0)
    
    # Incidents
    total_incidents = models.IntegerField(default=0)
    incidents_actifs = models.IntegerField(default=0)
    taux_resolution = models.FloatField(default=0)
    
    # Résultats (top 3)
    resultats_snapshot = models.JSONField(
        default=list,
        help_text="Snapshot des résultats principaux"
    )
    
    # Détails par région
    details_regions = models.JSONField(
        default=list,
        help_text="Détails statistiques par région"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'snapshots_quotidiens'
        verbose_name = 'Snapshot quotidien'
        verbose_name_plural = 'Snapshots quotidiens'
        ordering = ['-date']
    
    def __str__(self):
        return f"Snapshot {self.date}"
    
    @classmethod
    def creer_snapshot_aujourdhui(cls):
        """Crée le snapshot du jour"""
        from statistic.services import StatistiqueService
        
        service = StatistiqueService()
        data = service.calculer_snapshot_national()
        
        snapshot, created = cls.objects.update_or_create(
            date=timezone.now().date(),
            defaults=data
        )
        
        return snapshot