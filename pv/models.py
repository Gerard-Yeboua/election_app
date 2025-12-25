import uuid
from django.db import models

# Create your models here.
# pv/models.py
from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User
from geography.models import BureauVote
import cloudinary.models

# pv/models.py

class Candidat(models.Model):
    """Modèle des candidats aux élections"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_ordre = models.PositiveIntegerField(unique=True, verbose_name="Numéro d'ordre")
    nom_complet = models.CharField(max_length=200, verbose_name="Nom complet")
    parti_politique = models.CharField(max_length=200, blank=True, verbose_name="Parti politique")
    
    # AJOUTER CES DEUX CHAMPS
    est_independant = models.BooleanField(default=False, verbose_name="Candidat indépendant")
    est_actif = models.BooleanField(default=True, verbose_name="Actif")
    
    photo = models.ImageField(
        upload_to='candidats/',
        blank=True,
        null=True,
        verbose_name="Photo"
    )
    
    class Meta:
        db_table = 'pv_candidat'
        ordering = ['numero_ordre']
        verbose_name = 'Candidat'
        verbose_name_plural = 'Candidats'
    
    def __str__(self):
        return f"{self.numero_ordre} - {self.nom_complet}"

class ProcesVerbal(models.Model):
    """Procès-verbal d'un bureau de vote"""
    
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente de validation'),
        ('VALIDE', 'Validé'),
        ('REJETE', 'Rejeté'),
        ('CORRECTION', 'En correction'),
    ]
    
    # Identification
    numero_reference = models.CharField(max_length=50, unique=True, editable=False)
    bureau_vote = models.ForeignKey(BureauVote, on_delete=models.PROTECT, related_name='proces_verbaux')
    superviseur = models.ForeignKey(User, on_delete=models.PROTECT, related_name='pv_soumis')
    checkin = models.ForeignKey('accounts.CheckIn', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Données générales du bureau
    nombre_inscrits = models.IntegerField(validators=[MinValueValidator(0)])
    nombre_votants = models.IntegerField(validators=[MinValueValidator(0)])
    suffrages_exprimes = models.IntegerField(validators=[MinValueValidator(0)])
    bulletins_nuls = models.IntegerField(validators=[MinValueValidator(0)])
    bulletins_blancs = models.IntegerField(validators=[MinValueValidator(0)])
    
    # Photos via Cloudinary
    photo_pv_officiel = cloudinary.models.CloudinaryField('pv_officiel')
    photo_tableau_resultats = cloudinary.models.CloudinaryField('tableau_resultats', blank=True, null=True)
    
    # Géolocalisation et horodatage
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    date_soumission = models.DateTimeField(auto_now_add=True)
    
    # Validation
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    validateur = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='pv_valides'
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True, null=True)
    commentaires_validation = models.TextField(blank=True, null=True)
    
    # Flags de contrôle
    has_incoherence = models.BooleanField(default=False)
    erreurs_detectees = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'proces_verbaux'
        ordering = ['-date_soumission']
        verbose_name = 'Procès-verbal'
        verbose_name_plural = 'Procès-verbaux'
        unique_together = ['bureau_vote', 'date_soumission']

    def __str__(self):
        return f"PV {self.numero_reference} - {self.bureau_vote.code_bv}"
    
    def save(self, *args, **kwargs):
        # Génération automatique du numéro de référence
        if not self.numero_reference:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.numero_reference = f"PV-{self.bureau_vote.code_bv}-{timestamp}"
        
        # Validation des cohérences
        self.validate_coherence()
        
        super().save(*args, **kwargs)
    
    def validate_coherence(self):
        """Valide la cohérence des données saisies"""
        erreurs = []
        
        # Vérification 1: Votants <= Inscrits
        if self.nombre_votants > self.nombre_inscrits:
            erreurs.append("Le nombre de votants dépasse le nombre d'inscrits")
        
        # Vérification 2: Suffrages + Nuls + Blancs = Votants
        total = self.suffrages_exprimes + self.bulletins_nuls + self.bulletins_blancs
        if total != self.nombre_votants:
            erreurs.append(
                f"Incohérence: Suffrages ({self.suffrages_exprimes}) + "
                f"Nuls ({self.bulletins_nuls}) + Blancs ({self.bulletins_blancs}) "
                f"= {total} ≠ Votants ({self.nombre_votants})"
            )
        
        self.erreurs_detectees = erreurs
        self.has_incoherence = len(erreurs) > 0
    
    @property
    def total_voix_candidats(self):
        """Somme des voix de tous les candidats"""
        return self.resultats.aggregate(models.Sum('nombre_voix'))['nombre_voix__sum'] or 0
    
    @property
    def taux_participation(self):
        """Calcul du taux de participation"""
        if self.nombre_inscrits == 0:
            return 0
        return round((self.nombre_votants / self.nombre_inscrits) * 100, 2)


# pv/models.py

class ResultatCandidat(models.Model):
    """Résultats d'un candidat dans un bureau"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # VÉRIFIER QUE CE CHAMP EXISTE
    pv = models.ForeignKey(
        ProcesVerbal,
        on_delete=models.CASCADE,
        related_name='resultats'
    )
    
    candidat = models.ForeignKey(
        Candidat,
        on_delete=models.CASCADE,
        related_name='resultats'
    )
    
    nombre_voix = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Nombre de voix"
    )
    
    class Meta:
        db_table = 'pv_resultat_candidat'
        unique_together = ['pv', 'candidat']
        ordering = ['-nombre_voix']
        verbose_name = 'Résultat candidat'
        verbose_name_plural = 'Résultats candidats'
    
    def __str__(self):
        return f"{self.candidat.nom_complet} - {self.nombre_voix} voix"
    
    @property
    def pourcentage_bureau(self):
        """Calcul du pourcentage au bureau"""
        if self.pv.suffrages_exprimes > 0:
            return round((self.nombre_voix / self.pv.suffrages_exprimes) * 100, 2)
        return 0
    
    @property
    def position_bureau(self):
        """Position du candidat dans ce bureau"""
        resultats = ResultatCandidat.objects.filter(
            pv=self.pv
        ).order_by('-nombre_voix')
        
        for index, resultat in enumerate(resultats, start=1):
            if resultat.id == self.id:
                return index
        return None


class HistoriqueValidation(models.Model):
    """Historique des actions de validation sur un PV"""
    
    ACTION_CHOICES = [
        ('VALIDER', 'Valider'),
        ('REJETER', 'Rejeter'),
        ('CORRECTION', 'Demander correction'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pv = models.ForeignKey(
        'ProcesVerbal',
        on_delete=models.CASCADE,
        related_name='historique_validations'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    validateur = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='validations_effectuees'
    )
    date_action = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)
    motif_rejet = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pv_historique_validation'
        ordering = ['-date_action']
        verbose_name = 'Historique de validation'
        verbose_name_plural = 'Historiques de validation'
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.pv.numero_reference} - {self.date_action}"