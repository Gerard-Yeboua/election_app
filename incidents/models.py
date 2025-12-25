# incidents/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from accounts.models import User
from geography.models import BureauVote
from cloudinary.models import CloudinaryField
import uuid


class Incident(models.Model):
    """Incident signalé par un superviseur sur un bureau de vote"""
    
    CATEGORIE_CHOICES = [
        ('ABSENCE_ASSESSEURS', 'Absence d\'assesseurs'),
        ('MATERIEL_MANQUANT', 'Matériel manquant'),
        ('RETARD_OUVERTURE', 'Retard d\'ouverture'),
        ('RETARD_FERMETURE', 'Retard de fermeture'),
        ('PROBLEME_TECHNIQUE', 'Problème technique'),
        ('INCIDENT_SECURITAIRE', 'Incident sécuritaire'),
        ('FRAUDE_SUSPECTEE', 'Fraude suspectée'),
        ('AFFLUENCE_ANORMALE', 'Affluence anormale'),
        ('PROBLEME_ELECTRICITE', 'Problème d\'électricité'),
        ('PROBLEME_ACCES', 'Problème d\'accès au bureau'),
        ('CONFLIT', 'Conflit/Altercation'),
        ('AUTRE', 'Autre'),
    ]
    
    STATUT_CHOICES = [
        ('OUVERT', 'Ouvert'),
        ('EN_COURS', 'En cours de traitement'),
        ('TRAITE', 'Traité'),
        ('CLOS', 'Clos'),
    ]
    
    PRIORITE_CHOICES = [
        ('BASSE', 'Basse'),
        ('MOYENNE', 'Moyenne'),
        ('HAUTE', 'Haute'),
        ('URGENTE', 'Urgente'),
        ('CRITIQUE', 'Critique'),
    ]
    
    IMPACT_CHOICES = [
        ('FAIBLE', 'Faible'),
        ('MOYEN', 'Moyen'),
        ('ELEVE', 'Élevé'),
        ('CRITIQUE', 'Critique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_ticket = models.CharField(max_length=50, unique=True, editable=False)
    
    # Relations
    bureau_vote = models.ForeignKey(BureauVote, on_delete=models.PROTECT, related_name='incidents')
    superviseur = models.ForeignKey(User, on_delete=models.PROTECT, related_name='incidents_signales')
    
    # Détails
    categorie = models.CharField(max_length=30, choices=CATEGORIE_CHOICES)
    titre = models.CharField(max_length=200)
    description = models.TextField()
    heure_incident = models.DateTimeField()
    
    # Impact
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='MOYEN')
    vote_affecte = models.BooleanField(default=False)
    nombre_electeurs_impactes = models.IntegerField(null=True, blank=True)
    
    # Géolocalisation
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    
    # Gestion
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='OUVERT')
    priorite = models.CharField(max_length=20, choices=PRIORITE_CHOICES, default='MOYENNE')
    
    admin_responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents_responsable'
    )
    
    date_attribution = models.DateTimeField(null=True, blank=True)
    date_debut_traitement = models.DateTimeField(null=True, blank=True)
    date_resolution = models.DateTimeField(null=True, blank=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    
    solution = models.TextField(blank=True, null=True)
    actions_menees = models.TextField(blank=True, null=True)
    
    # Escalade
    escalade = models.BooleanField(default=False)
    date_escalade = models.DateTimeField(null=True, blank=True)
    motif_escalade = models.TextField(blank=True, null=True)
    
    # SLA
    delai_resolution_cible = models.IntegerField(default=240)
    temps_resolution = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'incidents'
        ordering = ['-created_at']
        verbose_name = 'Incident'
        verbose_name_plural = 'Incidents'
    
    def __str__(self):
        return f"{self.numero_ticket} - {self.get_categorie_display()}"
    
    def save(self, *args, **kwargs):
        if not self.numero_ticket:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_suffix = uuid.uuid4().hex[:4].upper()
            self.numero_ticket = f"INC-{self.bureau_vote.code_bv}-{timestamp}-{random_suffix}"
        
        if not self.titre:
            self.titre = f"{self.get_categorie_display()} - {self.bureau_vote.nom_bv}"
        
        super().save(*args, **kwargs)
    
    @property
    def temps_ouvert_minutes(self):
        """Temps depuis l'ouverture en minutes"""
        if self.statut == 'CLOS' and self.date_cloture:
            delta = self.date_cloture - self.created_at
        else:
            delta = timezone.now() - self.created_at
        return round(delta.total_seconds() / 60, 2)


class IncidentMessage(models.Model):
    """Messages échangés dans le cadre d'un incident"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='messages')
    auteur = models.ForeignKey(User, on_delete=models.PROTECT, related_name='messages_incidents')
    message = models.TextField()
    est_interne = models.BooleanField(default=False)
    est_lu = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incident_messages'
        ordering = ['created_at']
        verbose_name = 'Message incident'
        verbose_name_plural = 'Messages incidents'
    
    def __str__(self):
        return f"Message de {self.auteur.nom_complet} - {self.created_at}"


class IncidentPhoto(models.Model):
    """Photos associées à un incident"""
    
    TYPE_CHOICES = [
        ('PREUVE', 'Preuve de l\'incident'),
        ('CONTEXTE', 'Photo de contexte'),
        ('RESOLUTION', 'Photo de résolution'),
        ('AUTRE', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='photos')
    photo = CloudinaryField('incident_photo', folder='incidents/photos/')
    type_photo = models.CharField(max_length=20, choices=TYPE_CHOICES, default='PREUVE')
    legende = models.CharField(max_length=200, blank=True, null=True)
    ordre = models.IntegerField(default=0)
    date_prise = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incident_photos'
        ordering = ['ordre', 'date_prise']
        verbose_name = 'Photo incident'
        verbose_name_plural = 'Photos incidents'
    
    def __str__(self):
        return f"Photo {self.ordre} - Incident {self.incident.numero_ticket}"


class HistoriqueIncident(models.Model):
    """Historique des actions sur un incident"""
    
    ACTION_CHOICES = [
        ('CREER', 'Créer'),
        ('ATTRIBUER', 'Attribuer'),
        ('DEMARRER', 'Démarrer traitement'),
        ('RESOUDRE', 'Résoudre'),
        ('CLOTURER', 'Clôturer'),
        ('ESCALADER', 'Escalader'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='actions_incidents'
    )
    date_action = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    
    class Meta:
        db_table = 'incidents_historique'
        ordering = ['-date_action']
        verbose_name = 'Historique incident'
        verbose_name_plural = 'Historiques incidents'
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.incident.numero_ticket} - {self.date_action}"


class ModeleIncident(models.Model):
    """Modèles prédéfinis pour créer rapidement des incidents courants"""
    
    nom = models.CharField(max_length=200, unique=True)
    categorie = models.CharField(max_length=30, choices=Incident.CATEGORIE_CHOICES)
    titre_template = models.CharField(max_length=200)
    description_template = models.TextField()
    priorite_defaut = models.CharField(max_length=20, choices=Incident.PRIORITE_CHOICES, default='MOYENNE')
    impact_defaut = models.CharField(max_length=20, choices=Incident.IMPACT_CHOICES, default='MOYEN')
    instructions = models.TextField(blank=True, null=True)
    est_actif = models.BooleanField(default=True)
    nombre_utilisations = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'modeles_incidents'
        ordering = ['nom']
        verbose_name = 'Modèle d\'incident'
        verbose_name_plural = 'Modèles d\'incidents'
    
    def __str__(self):
        return f"{self.nom} ({self.get_categorie_display()})"