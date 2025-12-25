from django.db import models

# Create your models here.
# pv/models.py
from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User
from geography.models import BureauVote
import cloudinary.models

class Candidat(models.Model):
    """Candidat à l'élection"""
    nom_complet = models.CharField(max_length=200)
    parti_politique = models.CharField(max_length=200)
    numero_ordre = models.IntegerField()
    photo = cloudinary.models.CloudinaryField('candidat_photo', blank=True, null=True)
    
    # Peut être limité à certaines circonscriptions
    regions = models.ManyToManyField('geography.Region', blank=True, related_name='candidats')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'candidats'
        ordering = ['numero_ordre']
        verbose_name = 'Candidat'
        verbose_name_plural = 'Candidats'

    def __str__(self):
        return f"{self.numero_ordre}. {self.nom_complet} ({self.parti_politique})"


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


class ResultatCandidat(models.Model):
    """Résultat d'un candidat pour un PV donné"""
    proces_verbal = models.ForeignKey(ProcesVerbal, on_delete=models.CASCADE, related_name='resultats')
    candidat = models.ForeignKey(Candidat, on_delete=models.PROTECT)
    nombre_voix = models.IntegerField(validators=[MinValueValidator(0)])
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'resultats_candidats'
        unique_together = ['proces_verbal', 'candidat']
        verbose_name = 'Résultat candidat'
        verbose_name_plural = 'Résultats candidats'

    def __str__(self):
        return f"{self.candidat.nom_complet}: {self.nombre_voix} voix"


class ValidationHistory(models.Model):
    """Historique des validations d'un PV"""
    proces_verbal = models.ForeignKey(ProcesVerbal, on_delete=models.CASCADE, related_name='historique_validations')
    validateur = models.ForeignKey(User, on_delete=models.PROTECT)
    action = models.CharField(max_length=20)  # VALIDE, REJETE, CORRECTION
    commentaire = models.TextField(blank=True, null=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'validation_history'
        ordering = ['-date_action']
        