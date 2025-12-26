# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, Avg
from datetime import timedelta
from math import radians, sin, cos, sqrt, atan2
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
        extra_fields.setdefault('role', 'BACK_OFFICE')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser doit avoir is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    
    def back_office(self):
        """Retourne tous les utilisateurs back office"""
        return self.filter(role='BACK_OFFICE', is_active=True)
    
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
    # À ajouter dans la classe User, après les propriétés existantes

# ========== MÉTHODES D'ACCÈS ET PERMISSIONS ==========

    def a_acces_complet(self):
        """Le back office a un accès complet à tout"""
        return self.role == 'BACK_OFFICE' and self.is_active

    def peut_voir_region(self, region):
        """Vérifie si l'utilisateur peut voir une région"""
        if self.role == 'BACK_OFFICE':
            return True
        return self.region == region if self.region else False

    def peut_voir_departement(self, departement):
        """Vérifie si l'utilisateur peut voir un département"""
        if self.role == 'BACK_OFFICE':
            return True
        if self.departement:
            return self.departement == departement
        if self.region:
            return departement.region == self.region
        return False

    def peut_voir_commune(self, commune):
        """Vérifie si l'utilisateur peut voir une commune"""
        if self.role == 'BACK_OFFICE':
            return True
        if self.commune:
            return self.commune == commune
        if self.departement:
            return commune.departement == self.departement
        if self.region:
            return commune.departement.region == self.region
        return False

    def peut_voir_bureau(self, bureau_vote):
        """Vérifie si l'utilisateur peut voir un bureau de vote"""
        if self.role == 'BACK_OFFICE':
            return True
        if self.role == 'SUPERVISEUR':
            return self.bureau_vote == bureau_vote
        if self.lieu_vote:
            return bureau_vote.lieu_vote == self.lieu_vote
        if self.sous_prefecture:
            return bureau_vote.lieu_vote.sous_prefecture == self.sous_prefecture
        if self.commune:
            return bureau_vote.lieu_vote.sous_prefecture.commune == self.commune
        if self.region:
            return bureau_vote.lieu_vote.sous_prefecture.commune.departement.region == self.region
        return False

    def get_incidents_accessibles(self):
        """Retourne les incidents accessibles selon le rôle"""
        from incidents.models import Incident  # Import local pour éviter les imports circulaires
        
        if self.role == 'BACK_OFFICE':
            # Accès complet à tous les incidents
            return Incident.objects.all()
        
        elif self.role == 'SUPER_ADMIN':
            if self.region:
                return Incident.objects.filter(
                    bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self.region
                )
            return Incident.objects.none()
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return Incident.objects.filter(bureau_vote__lieu_vote=self.lieu_vote)
            elif self.sous_prefecture:
                return Incident.objects.filter(bureau_vote__lieu_vote__sous_prefecture=self.sous_prefecture)
            elif self.commune:
                return Incident.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune=self.commune)
            elif self.departement:
                return Incident.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune__departement=self.departement)
            elif self.region:
                return Incident.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self.region)
            return Incident.objects.none()
        
        elif self.role == 'SUPERVISEUR':
            if self.bureau_vote:
                return Incident.objects.filter(bureau_vote=self.bureau_vote)
            return Incident.objects.none()
        
        return Incident.objects.none()

    def get_pv_accessibles(self):
        """Retourne les PV accessibles selon le rôle"""
        from pv.models import PV  # Import local
        
        if self.role == 'BACK_OFFICE':
            return PV.objects.all()
        
        elif self.role == 'SUPER_ADMIN':
            if self.region:
                return PV.objects.filter(
                    bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self.region
                )
            return PV.objects.none()
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return PV.objects.filter(bureau_vote__lieu_vote=self.lieu_vote)
            elif self.sous_prefecture:
                return PV.objects.filter(bureau_vote__lieu_vote__sous_prefecture=self.sous_prefecture)
            elif self.commune:
                return PV.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune=self.commune)
            elif self.departement:
                return PV.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune__departement=self.departement)
            elif self.region:
                return PV.objects.filter(bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self.region)
            return PV.objects.none()
        
        elif self.role == 'SUPERVISEUR':
            return PV.objects.filter(superviseur=self)
        
        return PV.objects.none()

    def get_users_accessibles(self):
        """Retourne les utilisateurs accessibles selon le rôle"""
        if self.role == 'BACK_OFFICE':
            return User.objects.all()
        
        elif self.role == 'SUPER_ADMIN':
            if self.region:
                return User.objects.filter(region=self.region)
            return User.objects.none()
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return User.objects.filter(lieu_vote=self.lieu_vote)
            elif self.sous_prefecture:
                return User.objects.filter(sous_prefecture=self.sous_prefecture)
            elif self.commune:
                return User.objects.filter(commune=self.commune)
            elif self.departement:
                return User.objects.filter(departement=self.departement)
            elif self.region:
                return User.objects.filter(region=self.region)
            return User.objects.none()
        
        return User.objects.filter(pk=self.pk)

    def get_bureaux_vote_accessibles(self):
        """Retourne les bureaux de vote accessibles selon le rôle"""
        from geography.models import BureauVote  # Import local
        
        if self.role == 'BACK_OFFICE':
            return BureauVote.objects.all()
        
        elif self.role == 'SUPER_ADMIN':
            if self.region:
                return BureauVote.objects.filter(
                    lieu_vote__sous_prefecture__commune__departement__region=self.region
                )
            return BureauVote.objects.none()
        
        elif self.role == 'ADMIN':
            if self.lieu_vote:
                return BureauVote.objects.filter(lieu_vote=self.lieu_vote)
            elif self.sous_prefecture:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture=self.sous_prefecture)
            elif self.commune:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture__commune=self.commune)
            elif self.departement:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture__commune__departement=self.departement)
            elif self.region:
                return BureauVote.objects.filter(lieu_vote__sous_prefecture__commune__departement__region=self.region)
            return BureauVote.objects.none()
        
        elif self.role == 'SUPERVISEUR':
            if self.bureau_vote:
                return BureauVote.objects.filter(pk=self.bureau_vote.pk)
            return BureauVote.objects.none()
        
        return BureauVote.objects.none()

    def peut_creer_utilisateur(self):
        """Vérifie si l'utilisateur peut créer d'autres utilisateurs"""
        return self.role in ['BACK_OFFICE', 'SUPER_ADMIN', 'ADMIN']

    def peut_modifier_utilisateur(self, user):
        """Vérifie si l'utilisateur peut modifier un autre utilisateur"""
        if self.role == 'BACK_OFFICE':
            return True
        if self.role == 'SUPER_ADMIN':
            return user.region == self.region
        if self.role == 'ADMIN':
            return user.region == self.region
        return False

    def peut_supprimer_utilisateur(self, user):
        """Vérifie si l'utilisateur peut supprimer un autre utilisateur"""
        if self.role == 'BACK_OFFICE':
            return True
        if self.role == 'SUPER_ADMIN':
            return user.region == self.region and user.role not in ['BACK_OFFICE', 'SUPER_ADMIN']
        return False

    def peut_valider_pv(self):
        """Vérifie si l'utilisateur peut valider des PV"""
        return self.role in ['BACK_OFFICE', 'SUPER_ADMIN', 'ADMIN']

    def peut_exporter_rapports(self):
        """Vérifie si l'utilisateur peut exporter des rapports"""
        return self.role in ['BACK_OFFICE', 'SUPER_ADMIN', 'ADMIN']

    def peut_voir_statistiques_globales(self):
        """Vérifie si l'utilisateur peut voir les statistiques globales"""
        return self.role in ['BACK_OFFICE', 'SUPER_ADMIN']

    def peut_gerer_parametres_systeme(self):
        """Vérifie si l'utilisateur peut gérer les paramètres système"""
        return self.role == 'BACK_OFFICE'


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
        ('BACK_OFFICE', 'Back Office'),
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
    region = models.ForeignKey(
        'geography.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Région d'affectation (optionnel pour BACK_OFFICE)"
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
        
        # BACK_OFFICE : aucune restriction géographique requise
        if self.role == 'BACK_OFFICE':
            pass
        
        # SUPER_ADMIN : doit avoir au moins une région
        elif self.role == 'SUPER_ADMIN':
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
        if self.role == 'BACK_OFFICE':
            return "National - Accès complet"
        
        elif self.role == 'SUPER_ADMIN':
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
    def est_back_office(self):
        """Vérifie si l'utilisateur est back office"""
        return self.role == 'BACK_OFFICE'
    
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
    
    def get_performance_superviseur(self):
        """Statistiques de performance pour les superviseurs"""
        if self.role != 'SUPERVISEUR':
            return None
        
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
        
        return {
            'total_pv': total,
            'pv_valides': valides,
            'pv_rejetes': rejetes,
            'taux_validation': round((valides / total * 100), 2),
            'taux_rejet': round((rejetes / total * 100), 2),
        }


# ============================================================
# MODÈLE CHECK-IN
# ============================================================

class CheckIn(models.Model):
    """Historique des check-ins des superviseurs sur les bureaux de vote"""
    
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
    
    nom_saisi = models.CharField(max_length=200)
    
    # Géolocalisation
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    precision_gps = models.FloatField(null=True, blank=True)
    
    # Horodatage
    checkin_time = models.DateTimeField(auto_now_add=True)
    checkout_time = models.DateTimeField(null=True, blank=True)
    
    # Statut
    is_active = models.BooleanField(default=True)
    nom_valide = models.BooleanField(default=False)
    
    # Métadonnées
    device_info = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    distance_bureau = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkins'
        ordering = ['-checkin_time']
        verbose_name = 'Check-in'
        verbose_name_plural = 'Check-ins'
    
    def __str__(self):
        return f"{self.superviseur.nom_complet} - {self.bureau_vote.code_bv}"
    
    @property
    def duree_presence(self):
        """Calcule la durée de présence en minutes"""
        if not self.checkout_time:
            duree = timezone.now() - self.checkin_time
        else:
            duree = self.checkout_time - self.checkin_time
        return round(duree.total_seconds() / 60, 2)


# ============================================================
# MODÈLE PERMISSIONS
# ============================================================

class Permission(models.Model):
    """Permissions granulaires pour les utilisateurs"""
    
    PERMISSION_CHOICES = [
        ('create_user', 'Créer des utilisateurs'),
        ('edit_user', 'Modifier des utilisateurs'),
        ('delete_user', 'Supprimer des utilisateurs'),
        ('validate_pv', 'Valider des PV'),
        ('export_reports', 'Exporter des rapports'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='permissions_custom')
    permission_code = models.CharField(max_length=50, choices=PERMISSION_CHOICES)
    region = models.ForeignKey('geography.Region', on_delete=models.CASCADE, null=True, blank=True)
    
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='permissions_granted')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission_code', 'region']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return f"{self.user.nom_complet} - {self.get_permission_code_display()}"


# ============================================================
# MODÈLE HISTORIQUE CONNEXIONS
# ============================================================

class LoginHistory(models.Model):
    """Historique des connexions des utilisateurs"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    device_info = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        db_table = 'login_history'
        ordering = ['-login_time']
        verbose_name = 'Historique de connexion'
        verbose_name_plural = 'Historiques de connexions'
    
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
    """Log d'audit pour tracer toutes les actions importantes"""
    
    ACTION_CHOICES = [
        ('USER_CREATE', 'Création utilisateur'),
        ('USER_UPDATE', 'Modification utilisateur'),
        ('USER_DELETE', 'Suppression utilisateur'),
        ('PV_SUBMIT', 'Soumission PV'),
        ('PV_VALIDATE', 'Validation PV'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    target_model = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.CharField(max_length=100, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Log d\'audit'
        verbose_name_plural = 'Logs d\'audit'
    
    def __str__(self):
        return f"{self.user.nom_complet if self.user else 'Système'} - {self.get_action_display()}"