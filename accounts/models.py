from django.db import models

# Create your models here.
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
import uuid


# ============================================================
# MANAGERS PERSONNALISÉS
# ============================================================

class UserManager(BaseUserManager):
    """Manager personnalisé pour le modèle User"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Créer et sauvegarder un utilisateur normal"""
        if not email:
            raise ValueError("L'email est obligatoire")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Créer et sauvegarder un superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser doit avoir is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    
    def superviseurs(self):
        """Retourne tous les superviseurs"""
        return self.filter(role='SUPERVISEUR', is_active=True)
    
    def administrateurs(self):
        """Retourne tous les administrateurs"""
        return self.filter(role='ADMIN', is_active=True)
    
    def super_administrateurs(self):
        """Retourne tous les super administrateurs"""
        return self.filter(role='SUPER_ADMIN', is_active=True)
    
    def par_region(self, region):
        """Retourne les utilisateurs d'une région"""
        return self.filter(region=region, is_active=True)
    
    def par_bureau(self, bureau_vote):
        """Retourne le superviseur d'un bureau"""
        return self.filter(bureau_vote=bureau_vote, role='SUPERVISEUR', is_active=True).first()


# ============================================================
# MODÈLE USER
# ============================================================

class User(AbstractUser):
    """
    Utilisateur personnalisé avec système de rôles hiérarchiques
    et affectations géographiques granulaires
    """
    
    # Choix de rôles
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Administrateur'),
        ('ADMIN', 'Administrateur'),
        ('SUPERVISEUR', 'Superviseur'),
    ]
    
    # Remplacer username par email comme identifiant principal
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, verbose_name="Email")
    
    # Informations personnelles
    telephone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?225?\d{8,10}$',
                message="Format: +225XXXXXXXX ou 225XXXXXXXX"
            )
        ]
    )
    
    # Informations complémentaires
    matricule = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text="Matricule de l'agent"
    )
    photo = models.ImageField(
        upload_to='users/photos/',
        blank=True,
        null=True
    )
    
    # Rôle et statut
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='SUPERVISEUR'
    )
    is_active = models.BooleanField(default=True)
    
    # Affectations géographiques hiérarchiques
    # NULL = accès à tous les niveaux inférieurs
    region = models.ForeignKey(
        'geography.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Région d'affectation"
    )
    
    departement = models.ForeignKey(
        'geography.Departement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Département d'affectation (optionnel)"
    )
    
    commune = models.ForeignKey(
        'geography.Commune',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Commune d'affectation (optionnel)"
    )
    
    sous_prefecture = models.ForeignKey(
        'geography.SousPrefecture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Sous-préfecture d'affectation (optionnel)"
    )
    
    lieu_vote = models.ForeignKey(
        'geography.LieuVote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Lieu de vote d'affectation (optionnel)"
    )
    
    bureau_vote = models.ForeignKey(
        'geography.BureauVote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superviseurs',
        help_text="Bureau de vote d'affectation (obligatoire pour superviseur)"
    )
    
    # Métadonnées
    date_embauche = models.DateField(blank=True, null=True)
    commentaire = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        help_text="Utilisateur qui a créé ce compte"
    )
    
    # Gestion des sessions
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    login_count = models.IntegerField(default=0)
    
    # Manager personnalisé
    objects = UserManager()
    
    # Utiliser email comme identifiant principal
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['region', 'role']),
            models.Index(fields=['bureau_vote']),
            models.Index(fields=['matricule']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # Auto-générer username depuis email si non fourni
        if not self.username:
            self.username = self.email.split('@')[0]
        
        # Valider avant sauvegarde
        self.clean()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validation des affectations géographiques selon le rôle"""
        super().clean()
        
        # SUPER_ADMIN : doit avoir au moins une région
        if self.role == 'SUPER_ADMIN':
            if not self.region:
                raise ValidationError({
                    'region': "Un Super Admin doit être affecté à au moins une région"
                })
        
        # ADMIN : doit avoir au moins une région
        elif self.role == 'ADMIN':
            if not self.region:
                raise ValidationError({
                    'region': "Un Admin doit être affecté à au moins une région"
                })
        
        # SUPERVISEUR : doit avoir un bureau de vote
        elif self.role == 'SUPERVISEUR':
            if not self.bureau_vote:
                raise ValidationError({
                    'bureau_vote': "Un Superviseur doit être affecté à un bureau de vote"
                })
            
            # Auto-remplissage de la hiérarchie depuis le bureau
            if self.bureau_vote:
                self.lieu_vote = self.bureau_vote.lieu_vote
                self.sous_prefecture = self.bureau_vote.lieu_vote.sous_prefecture
                self.commune = self.bureau_vote.lieu_vote.sous_prefecture.commune
                self.departement = self.bureau_vote.lieu_vote.sous_prefecture.commune.departement
                self.region = self.bureau_vote.lieu_vote.sous_prefecture.commune.departement.region
        
        # Vérifier la cohérence de la hiérarchie si plusieurs niveaux sont renseignés
        if self.bureau_vote and self.lieu_vote:
            if self.bureau_vote.lieu_vote != self.lieu_vote:
                raise ValidationError({
                    'bureau_vote': "Le bureau de vote doit appartenir au lieu de vote sélectionné"
                })
        
        if self.lieu_vote and self.sous_prefecture:
            if self.lieu_vote.sous_prefecture != self.sous_prefecture:
                raise ValidationError({
                    'lieu_vote': "Le lieu de vote doit appartenir à la sous-préfecture sélectionnée"
                })
        
        if self.sous_prefecture and self.commune:
            if self.sous_prefecture.commune != self.commune:
                raise ValidationError({
                    'sous_prefecture': "La sous-préfecture doit appartenir à la commune sélectionnée"
                })
        
        if self.commune and self.departement:
            if self.commune.departement != self.departement:
                raise ValidationError({
                    'commune': "La commune doit appartenir au département sélectionné"
                })
        
        if self.departement and self.region:
            if self.departement.region != self.region:
                raise ValidationError({
                    'departement': "Le département doit appartenir à la région sélectionnée"
                })
    
    # ========== PROPRIÉTÉS ==========
    
    @property
    def nom_complet(self):
        """Retourne le nom complet"""
        return self.get_full_name() or self.email
    
    @property
    def initiales(self):
        """Retourne les initiales"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.email[0:2].upper()
    
    @property
    def perimetre_geographique(self):
        """Retourne le périmètre géographique de l'utilisateur"""
        if self.role == 'SUPER_ADMIN':
            if self.region:
                return f"Région: {self.region.nom_region}"
            return "National"
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return f"Lieu de vote: {self.lieu_vote.nom_lv}"
            elif self.sous_prefecture:
                return f"Sous-préfecture: {self.sous_prefecture.nom_sous_prefecture}"
            elif self.commune:
                return f"Commune: {self.commune.nom_commune}"
            elif self.departement:
                return f"Département: {self.departement.nom_departement}"
            elif self.region:
                return f"Région: {self.region.nom_region}"
            return "Non défini"
        
        elif self.role == 'SUPERVISEUR':
            if self.bureau_vote:
                return f"Bureau: {self.bureau_vote.code_bv}"
            return "Non affecté"
        
        return "Non défini"
    
    @property
    def niveau_acces(self):
        """Retourne le niveau d'accès le plus précis"""
        if self.bureau_vote:
            return ('bureau_vote', self.bureau_vote)
        elif self.lieu_vote:
            return ('lieu_vote', self.lieu_vote)
        elif self.sous_prefecture:
            return ('sous_prefecture', self.sous_prefecture)
        elif self.commune:
            return ('commune', self.commune)
        elif self.departement:
            return ('departement', self.departement)
        elif self.region:
            return ('region', self.region)
        return ('national', None)
    
    @property
    def est_superviseur(self):
        """Vérifie si l'utilisateur est superviseur"""
        return self.role == 'SUPERVISEUR'
    
    @property
    def est_admin(self):
        """Vérifie si l'utilisateur est administrateur"""
        return self.role == 'ADMIN'
    
    @property
    def est_super_admin(self):
        """Vérifie si l'utilisateur est super administrateur"""
        return self.role == 'SUPER_ADMIN'
    
    @property
    def peut_creer_utilisateurs(self):
        """Vérifie si l'utilisateur peut créer d'autres utilisateurs"""
        return self.role in ['SUPER_ADMIN', 'ADMIN']
    
    @property
    def peut_valider_pv(self):
        """Vérifie si l'utilisateur peut valider des PV"""
        return self.role in ['SUPER_ADMIN', 'ADMIN']
    
    @property
    def peut_soumettre_pv(self):
        """Vérifie si l'utilisateur peut soumettre des PV"""
        return self.role == 'SUPERVISEUR'
    
    # ========== MÉTHODES DE SCOPE ==========
    
    def get_bureaux_accessibles(self):
        """Retourne les bureaux de vote accessibles à l'utilisateur"""
        from  geography.models import BureauVote
        
        if self.role == 'SUPER_ADMIN':
            if self.region:
                return BureauVote.objects.filter(
                    lieu_vote__sous_prefecture__commune__departement__region=self.region
                )
            return BureauVote.objects.all()
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return BureauVote.objects.filter(lieu_vote=self.lieu_vote)
            elif self.sous_prefecture:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture=self.sous_prefecture)
            elif self.commune:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture__commune=self.commune)
            elif self.departement:
                return BureauVote.objects.filter(
                    lieu_vote__sous_prefecture__commune__departement=self.departement
                )
            elif self.region:
                return BureauVote.objects.filter(
                    lieu_vote__sous_prefecture__commune__departement__region=self.region
                )
        
        elif self.role == 'SUPERVISEUR':
            if self.bureau_vote:
                return BureauVote.objects.filter(id=self.bureau_vote.id)
        
        return BureauVote.objects.none()
    
    def get_pv_accessibles(self):
        """Retourne les PV accessibles à l'utilisateur"""
        from  pv.models import ProcesVerbal
        
        bureaux = self.get_bureaux_accessibles()
        return ProcesVerbal.objects.filter(bureau_vote__in=bureaux)
    
    def get_incidents_accessibles(self):
        """Retourne les incidents accessibles à l'utilisateur"""
        from  incidents.models import Incident
        
        bureaux = self.get_bureaux_accessibles()
        return Incident.objects.filter(bureau_vote__in=bureaux)
    
    def get_utilisateurs_geres(self):
        """Retourne les utilisateurs que cet utilisateur peut gérer"""
        if self.role == 'SUPER_ADMIN':
            # Peut gérer tous les utilisateurs de sa région
            if self.region:
                return User.objects.filter(region=self.region)
            return User.objects.all()
        
        elif self.role == 'ADMIN':
            # Peut gérer les superviseurs de son périmètre
            bureaux = self.get_bureaux_accessibles()
            return User.objects.filter(
                role='SUPERVISEUR',
                bureau_vote__in=bureaux
            )
        
        return User.objects.none()
    
    def peut_gerer_utilisateur(self, autre_user):
        """Vérifie si cet utilisateur peut gérer un autre utilisateur"""
        if not self.peut_creer_utilisateurs:
            return False
        
        return autre_user in self.get_utilisateurs_geres()
    
    def peut_acceder_bureau(self, bureau_vote):
        """Vérifie si l'utilisateur peut accéder à un bureau spécifique"""
        return bureau_vote in self.get_bureaux_accessibles()
    
    def peut_valider_pv_bureau(self, bureau_vote):
        """Vérifie si l'utilisateur peut valider un PV d'un bureau"""
        if not self.peut_valider_pv:
            return False
        return self.peut_acceder_bureau(bureau_vote)
    
    # ========== STATISTIQUES UTILISATEUR ==========
    
    def get_stats_activite(self):
        """Statistiques d'activité de l'utilisateur"""
        if self.role == 'SUPERVISEUR':
            return {
                'pv_soumis': self.pv_soumis.count(),
                'pv_valides': self.pv_soumis.filter(statut='VALIDE').count(),
                'pv_rejetes': self.pv_soumis.filter(statut='REJETE').count(),
                'incidents_signales': self.incidents_signales.count(),
                'checkins': self.checkins.count(),
                'dernier_checkin': self.checkins.order_by('-checkin_time').first(),
            }
        
        elif self.role in ['ADMIN', 'SUPER_ADMIN']:
            return {
                'pv_valides': self.pv_valides.count(),
                'incidents_traites': self.incidents_traites.filter(statut__in=['TRAITE', 'CLOS']).count(),
                'utilisateurs_crees': self.created_users.count(),
            }
        
        return {}
    
    def get_performance_superviseur(self):
        """Performance d'un superviseur (taux de validation, délais moyens, etc.)"""
        if self.role != 'SUPERVISEUR':
            return None
        
        from django.db.models import Avg
        from django.utils import timezone
        from datetime import timedelta
        
        pv_soumis = self.pv_soumis.all()
        total = pv_soumis.count()
        
        if total == 0:
            return {
                'total_pv': 0,
                'taux_validation': 0,
                'taux_rejet': 0,
                'delai_moyen_validation': 0,
            }
        
        valides = pv_soumis.filter(statut='VALIDE').count()
        rejetes = pv_soumis.filter(statut='REJETE').count()
        
        # Calcul du délai moyen de validation
        pv_avec_delai = pv_soumis.filter(
            statut='VALIDE',
            date_validation__isnull=False
        )
        
        delai_moyen = None
        if pv_avec_delai.exists():
            delais = [
                (pv.date_validation - pv.date_soumission).total_seconds() / 3600
                for pv in pv_avec_delai
            ]
            delai_moyen = sum(delais) / len(delais)
        
        return {
            'total_pv': total,
            'pv_valides': valides,
            'pv_rejetes': rejetes,
            'taux_validation': round((valides / total * 100), 2),
            'taux_rejet': round((rejetes / total * 100), 2),
            'delai_moyen_validation_heures': round(delai_moyen, 2) if delai_moyen else None,
        }


# ============================================================
# MODÈLE CHECK-IN
# ============================================================

class CheckIn(models.Model):
    """
    Historique des check-ins des superviseurs sur les bureaux de vote
    Permet de tracer la présence et l'activité terrain
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    superviseur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='checkins',
        limit_choices_to={'role': 'SUPERVISEUR'}
    )
    
    bureau_vote = models.ForeignKey(
        'geography.BureauVote',
        on_delete=models.CASCADE,
        related_name='checkins'
    )
    
    # Données du check-in
    nom_saisi = models.CharField(
        max_length=200,
        help_text="Nom complet saisi lors du check-in (doit correspondre exactement)"
    )
    
    # Géolocalisation
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Latitude GPS au moment du check-in"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        help_text="Longitude GPS au moment du check-in"
    )
    precision_gps = models.FloatField(
        null=True,
        blank=True,
        help_text="Précision GPS en mètres"
    )
    
    # Horodatage
    checkin_time = models.DateTimeField(auto_now_add=True)
    checkout_time = models.DateTimeField(null=True, blank=True)
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        help_text="True si le superviseur est actuellement en check-in"
    )
    
    # Validation du nom
    nom_valide = models.BooleanField(
        default=False,
        help_text="True si le nom saisi correspond au nom enregistré"
    )
    
    # Métadonnées
    device_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="Informations sur l'appareil utilisé"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Distance par rapport au bureau
    distance_bureau = models.FloatField(
        null=True,
        blank=True,
        help_text="Distance en mètres entre le check-in et le bureau de vote"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkins'
        ordering = ['-checkin_time']
        verbose_name = 'Check-in'
        verbose_name_plural = 'Check-ins'
        indexes = [
            models.Index(fields=['superviseur', 'checkin_time']),
            models.Index(fields=['bureau_vote', 'is_active']),
            models.Index(fields=['is_active', 'checkout_time']),
            models.Index(fields=['checkin_time']),
        ]
    
    def __str__(self):
        return f"{self.superviseur.nom_complet} - {self.bureau_vote.code_bv} ({self.checkin_time})"
    
    def clean(self):
        """Validation du check-in"""
        super().clean()
        
        # Vérifier que le superviseur est bien affecté à ce bureau
        if self.superviseur.bureau_vote != self.bureau_vote:
            raise ValidationError({
                'bureau_vote': f"Le superviseur n'est pas affecté à ce bureau. "
                              f"Bureau affecté: {self.superviseur.bureau_vote.code_bv if self.superviseur.bureau_vote else 'Aucun'}"
            })
        
        # Vérifier qu'il n'y a pas déjà un check-in actif pour ce superviseur
        if self.is_active and not self.pk:  # Nouveau check-in
            checkin_actif = CheckIn.objects.filter(
                superviseur=self.superviseur,
                is_active=True,
                checkout_time__isnull=True
            ).exclude(pk=self.pk).exists()
            
            if checkin_actif:
                raise ValidationError({
                    'superviseur': "Ce superviseur a déjà un check-in actif. "
                                  "Veuillez effectuer un checkout d'abord."
                })
        
        # Validation du nom saisi
        nom_complet_attendu = self.superviseur.get_full_name().strip().lower()
        nom_saisi_clean = self.nom_saisi.strip().lower()
        
        self.nom_valide = (nom_complet_attendu == nom_saisi_clean)
        
        if not self.nom_valide:
            raise ValidationError({
                'nom_saisi': f"Le nom saisi ne correspond pas au nom enregistré. "
                           f"Attendu: '{self.superviseur.get_full_name()}'"
            })
    
    def save(self, *args, **kwargs):
        # Calculer la distance si les coordonnées du bureau sont disponibles
        if self.bureau_vote.lieu_vote.latitude and self.bureau_vote.lieu_vote.longitude:
            self.distance_bureau = self.calculer_distance(
                self.latitude,
                self.longitude,
                float(self.bureau_vote.lieu_vote.latitude),
                float(self.bureau_vote.lieu_vote.longitude)
            )
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def calculer_distance(lat1, lon1, lat2, lon2):
        """Calcule la distance entre deux points GPS en mètres (formule de Haversine)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Rayon de la Terre en mètres
        
        lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        return round(distance, 2)
    
    def effectuer_checkout(self):
        """Effectue le checkout du superviseur"""
        if not self.is_active:
            raise ValidationError("Ce check-in n'est plus actif")
        
        if self.checkout_time:
            raise ValidationError("Le checkout a déjà été effectué")
        
        self.checkout_time = timezone.now()
        self.is_active = False
        self.save()
    
    @property
    def duree_presence(self):
        """Calcule la durée de présence en minutes"""
        if not self.checkout_time:
            # Si pas encore de checkout, calculer depuis maintenant
            duree = timezone.now() - self.checkin_time
        else:
            duree = self.checkout_time - self.checkin_time
        
        return round(duree.total_seconds() / 60, 2)
    
    @property
    def est_dans_perimetre_autorise(self):
        """Vérifie si le check-in est dans un périmètre acceptable (500m)"""
        if self.distance_bureau is None:
            return None
        return self.distance_bureau <= 500  # 500 mètres
    
    @property
    def statut_presence(self):
        """Retourne le statut de présence"""
        if self.is_active and not self.checkout_time:
            return "En service"
        elif self.checkout_time:
            return "Terminé"
        else:
            return "Inactif"


# ============================================================
# MODÈLE PERMISSIONS / AUTORISATIONS
# ============================================================

class Permission(models.Model):
    """
    Permissions granulaires pour les utilisateurs
    Permet de gérer des autorisations spécifiques au-delà des rôles
    """
    
    PERMISSION_CHOICES = [
        # Gestion des utilisateurs
        ('create_user', 'Créer des utilisateurs'),
        ('edit_user', 'Modifier des utilisateurs'),
        ('delete_user', 'Supprimer des utilisateurs'),
        ('view_all_users', 'Voir tous les utilisateurs'),
        
        # Gestion des PV
        ('submit_pv', 'Soumettre des PV'),
        ('validate_pv', 'Valider des PV'),
        ('reject_pv', 'Rejeter des PV'),
        ('delete_pv', 'Supprimer des PV'),
        ('export_pv', 'Exporter des PV'),
        
        # Gestion des incidents
        ('create_incident', 'Créer des incidents'),
        ('assign_incident', 'Assigner des incidents'),
        ('resolve_incident', 'Résoudre des incidents'),
        ('close_incident', 'Clôturer des incidents'),
        
        # Configuration système
        ('manage_candidats', 'Gérer les candidats'),
        ('manage_bureaux', 'Gérer les bureaux de vote'),
        ('configure_system', 'Configurer le système'),
        
        # Rapports et exports
        ('view_statistics', 'Voir les statistiques'),
        ('export_reports', 'Exporter des rapports'),
        ('view_audit_logs', 'Voir les logs d\'audit'),
        
        # Notifications
        ('send_notifications', 'Envoyer des notifications'),
        ('manage_notifications', 'Gérer les notifications'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='permissions_custom'
    )
    
    permission_code = models.CharField(
        max_length=50,
        choices=PERMISSION_CHOICES
    )
    
    # Périmètre de la permission (optionnel)
    region = models.ForeignKey(
        'geography.Region',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Limiter la permission à une région spécifique"
    )
    
    # Métadonnées
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='permissions_granted'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date d'expiration de la permission (optionnel)"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission_code', 'region']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        indexes = [
            models.Index(fields=['user', 'permission_code']),
            models.Index(fields=['permission_code', 'is_active']),
        ]
    
    def __str__(self):
        region_str = f" ({self.region.nom_region})" if self.region else ""
        return f"{self.user.nom_complet} - {self.get_permission_code_display()}{region_str}"
    
    def clean(self):
        """Validation de la permission"""
        super().clean()
        
        # Vérifier l'expiration
        if self.expires_at and self.expires_at < timezone.now():
            raise ValidationError({
                'expires_at': "La date d'expiration ne peut pas être dans le passé"
            })
    
    @property
    def est_expire(self):
        """Vérifie si la permission est expirée"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def est_valide(self):
        """Vérifie si la permission est valide"""
        return self.is_active and not self.est_expire


# ============================================================
# MODÈLE HISTORIQUE CONNEXIONS
# ============================================================

class LoginHistory(models.Model):
    """Historique des connexions des utilisateurs"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    device_info = models.JSONField(default=dict, blank=True)
    
    # Géolocalisation (optionnel)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    
    # Statut
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        db_table = 'login_history'
        ordering = ['-login_time']
        verbose_name = 'Historique de connexion'
        verbose_name_plural = 'Historiques de connexions'
        indexes = [
            models.Index(fields=['user', 'login_time']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.nom_complet} - {self.login_time}"
    
    @property
    def duree_session(self):
        """Calcule la durée de la session en minutes"""
        if not self.logout_time:
            return None
        duree = self.logout_time - self.login_time
        return round(duree.total_seconds() / 60, 2)


# ============================================================
# MODÈLE AUDIT LOG
# ============================================================

class AuditLog(models.Model):
    """
    Log d'audit pour tracer toutes les actions importantes
    dans le système
    """
    
    ACTION_CHOICES = [
        ('USER_CREATE', 'Création utilisateur'),
        ('USER_UPDATE', 'Modification utilisateur'),
        ('USER_DELETE', 'Suppression utilisateur'),
        ('PV_SUBMIT', 'Soumission PV'),
        ('PV_VALIDATE', 'Validation PV'),
        ('PV_REJECT', 'Rejet PV'),
        ('INCIDENT_CREATE', 'Création incident'),
        ('INCIDENT_RESOLVE', 'Résolution incident'),
        ('CHECKIN', 'Check-in'),
        ('CHECKOUT', 'Check-out'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('CONFIG_CHANGE', 'Modification configuration'),
        ('EXPORT', 'Export de données'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Qui ?
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # Quoi ?
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Sur quoi ?
    target_model = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Détails
    details = models.JSONField(default=dict, blank=True)
    
    # Quand et où ?
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Log d\'audit'
        verbose_name_plural = 'Logs d\'audit'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.nom_complet if self.user else 'Système'} - {self.get_action_display()} - {self.timestamp}"
    
    @staticmethod
    def log(user, action, description, target_model=None, target_id=None, details=None, ip_address=None):
        """Méthode utilitaire pour créer un log d'audit"""
        return AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            target_model=target_model,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address
        )