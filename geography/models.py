from django.db import models

# Create your models here.
# apps/geography/models.py
from django.db import models
from django.db.models import Sum, Count, Avg, Q, F
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator




class BaseGeoModel(models.Model):
    """Modèle abstrait de base pour les entités géographiques"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Region(BaseGeoModel):
    """Région administrative - Niveau 1"""
    code_region = models.CharField(
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_region = models.CharField(max_length=200)
    
    # Métadonnées
    population = models.IntegerField(default=0, help_text="Population totale de la région")
    superficie = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Superficie en km²"
    )
    
    class Meta:
        db_table = 'geo_regions'
        ordering = ['nom_region']
        verbose_name = 'Région'
        verbose_name_plural = 'Régions'
        indexes = [
            models.Index(fields=['code_region']),
            models.Index(fields=['nom_region']),
        ]

    def __str__(self):
        return f"{self.code_region} - {self.nom_region}"
    
    # ========== STATISTIQUES RÉGION ==========
    
    @property
    def stats_bureaux(self):
        """Statistiques des bureaux de vote de la région"""
        
        
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture__commune__departement__region=self
        )
        
        return {
            'total': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'moyenne_inscrits': bureaux.aggregate(Avg('nombre_inscrits'))['nombre_inscrits__avg'] or 0,
        }
    
    @property
    def stats_pv(self):
        """Statistiques des PV de la région"""
        from  pv.models import ProcesVerbal
        
        pv_region = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self
        )
        
        total_bureaux = self.stats_bureaux['total']
        total_pv = pv_region.count()
        
        return {
            'total_pv': total_pv,
            'pv_en_attente': pv_region.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_region.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_region.filter(statut='REJETE').count(),
            'pv_en_correction': pv_region.filter(statut='CORRECTION').count(),
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round(
                (pv_region.filter(statut='VALIDE').count() / total_pv * 100), 2
            ) if total_pv > 0 else 0,
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation de la région"""
        from  pv.models import ProcesVerbal
        
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self,
            statut='VALIDE'
        )
        
        total_inscrits = pv_valides.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        total_votants = pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0
        total_exprimes = pv_valides.aggregate(Sum('suffrages_exprimes'))['suffrages_exprimes__sum'] or 0
        total_nuls = pv_valides.aggregate(Sum('bulletins_nuls'))['bulletins_nuls__sum'] or 0
        total_blancs = pv_valides.aggregate(Sum('bulletins_blancs'))['bulletins_blancs__sum'] or 0
        
        return {
            'total_inscrits': total_inscrits,
            'total_votants': total_votants,
            'total_exprimes': total_exprimes,
            'total_nuls': total_nuls,
            'total_blancs': total_blancs,
            'taux_participation': round((total_votants / total_inscrits * 100), 2) if total_inscrits > 0 else 0,
            'taux_nuls': round((total_nuls / total_votants * 100), 2) if total_votants > 0 else 0,
            'taux_blancs': round((total_blancs / total_votants * 100), 2) if total_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents de la région"""
        from  incidents.models import Incident
        
        incidents = Incident.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self
        )
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour la région"""
        from  pv.models import ResultatCandidat, ProcesVerbal
        
        resultats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')
        
        total_voix = sum(r['total_voix'] for r in resultats)
        
        return [
            {
                'candidat': r['candidat__nom_complet'],
                'parti': r['candidat__parti_politique'],
                'numero': r['candidat__numero_ordre'],
                'voix': r['total_voix'],
                'pourcentage': round((r['total_voix'] / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    def get_stats_par_departement(self):
        """Statistiques détaillées par département"""
        stats = []
        for dept in self.departements.all():
            stats.append({
                'departement': dept.nom_departement,
                'code': dept.code_departement,
                'bureaux': dept.stats_bureaux,
                'pv': dept.stats_pv,
                'participation': dept.stats_participation,
                'incidents': dept.stats_incidents,
            })
        return stats
    
    def get_evolution_soumissions(self, jours=7):
        """Évolution des soumissions de PV sur N jours"""
        from  pv.models import ProcesVerbal
        from django.utils import timezone
        from datetime import timedelta
        
        date_debut = timezone.now() - timedelta(days=jours)
        
        evolution = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement__region=self,
            date_soumission__gte=date_debut
        ).extra(
            select={'date': 'DATE(date_soumission)'}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return list(evolution)


class Departement(BaseGeoModel):
    """Département - Niveau 2"""
    region = models.ForeignKey(
        Region, 
        on_delete=models.CASCADE, 
        related_name='departements'
    )
    code_departement = models.CharField(
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_departement = models.CharField(max_length=200)
    
    # Métadonnées
    chef_lieu = models.CharField(max_length=200, blank=True, null=True)
    population = models.IntegerField(default=0)

    class Meta:
        db_table = 'geo_departements'
        ordering = ['nom_departement']
        verbose_name = 'Département'
        verbose_name_plural = 'Départements'
        indexes = [
            models.Index(fields=['code_departement']),
            models.Index(fields=['region', 'nom_departement']),
        ]

    def __str__(self):
        return f"{self.code_departement} - {self.nom_departement}"
    
    # ========== STATISTIQUES DÉPARTEMENT ==========
    
    @property
    def stats_bureaux(self):
        """Statistiques des bureaux de vote du département"""
        from  geography.models import BureauVote
        
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture__commune__departement=self
        )
        
        return {
            'total': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'moyenne_inscrits': bureaux.aggregate(Avg('nombre_inscrits'))['nombre_inscrits__avg'] or 0,
        }
    
    @property
    def stats_pv(self):
        """Statistiques des PV du département"""
        from  pv.models import ProcesVerbal
        
        pv_dept = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement=self
        )
        
        total_bureaux = self.stats_bureaux['total']
        total_pv = pv_dept.count()
        
        return {
            'total_pv': total_pv,
            'pv_en_attente': pv_dept.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_dept.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_dept.filter(statut='REJETE').count(),
            'pv_en_correction': pv_dept.filter(statut='CORRECTION').count(),
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round(
                (pv_dept.filter(statut='VALIDE').count() / total_pv * 100), 2
            ) if total_pv > 0 else 0,
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation du département"""
        from  pv.models import ProcesVerbal
        
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement=self,
            statut='VALIDE'
        )
        
        total_inscrits = pv_valides.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        total_votants = pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0
        total_exprimes = pv_valides.aggregate(Sum('suffrages_exprimes'))['suffrages_exprimes__sum'] or 0
        total_nuls = pv_valides.aggregate(Sum('bulletins_nuls'))['bulletins_nuls__sum'] or 0
        total_blancs = pv_valides.aggregate(Sum('bulletins_blancs'))['bulletins_blancs__sum'] or 0
        
        return {
            'total_inscrits': total_inscrits,
            'total_votants': total_votants,
            'total_exprimes': total_exprimes,
            'total_nuls': total_nuls,
            'total_blancs': total_blancs,
            'taux_participation': round((total_votants / total_inscrits * 100), 2) if total_inscrits > 0 else 0,
            'taux_nuls': round((total_nuls / total_votants * 100), 2) if total_votants > 0 else 0,
            'taux_blancs': round((total_blancs / total_votants * 100), 2) if total_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents du département"""
        from  incidents.models import Incident
        
        incidents = Incident.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune__departement=self
        )
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour le département"""
        from  pv.models import ResultatCandidat
        
        resultats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune__departement=self,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')
        
        total_voix = sum(r['total_voix'] for r in resultats)
        
        return [
            {
                'candidat': r['candidat__nom_complet'],
                'parti': r['candidat__parti_politique'],
                'numero': r['candidat__numero_ordre'],
                'voix': r['total_voix'],
                'pourcentage': round((r['total_voix'] / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    def get_stats_par_commune(self):
        """Statistiques détaillées par commune"""
        stats = []
        for commune in self.communes.all():
            stats.append({
                'commune': commune.nom_commune,
                'code': commune.code_commune,
                'bureaux': commune.stats_bureaux,
                'pv': commune.stats_pv,
                'participation': commune.stats_participation,
                'incidents': commune.stats_incidents,
            })
        return stats


class Commune(BaseGeoModel):
    """Commune - Niveau 3"""
    departement = models.ForeignKey(
        Departement, 
        on_delete=models.CASCADE, 
        related_name='communes'
    )
    code_commune = models.CharField(
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_commune = models.CharField(max_length=200)
    
    # Métadonnées
    population = models.IntegerField(default=0)
    type_commune = models.CharField(
        max_length=20,
        choices=[
            ('URBAINE', 'Urbaine'),
            ('RURALE', 'Rurale'),
        ],
        default='RURALE'
    )

    class Meta:
        db_table = 'geo_communes'
        ordering = ['nom_commune']
        verbose_name = 'Commune'
        verbose_name_plural = 'Communes'
        indexes = [
            models.Index(fields=['code_commune']),
            models.Index(fields=['departement', 'nom_commune']),
        ]

    def __str__(self):
        return f"{self.code_commune} - {self.nom_commune}"
    
    # ========== STATISTIQUES COMMUNE ==========
    
    @property
    def stats_bureaux(self):
        """Statistiques des bureaux de vote de la commune"""
        from  geography.models import BureauVote
        
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture__commune=self
        )
        
        return {
            'total': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'moyenne_inscrits': bureaux.aggregate(Avg('nombre_inscrits'))['nombre_inscrits__avg'] or 0,
        }
    
    @property
    def stats_pv(self):
        """Statistiques des PV de la commune"""
        from  pv.models import ProcesVerbal
        
        pv_commune = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune=self
        )
        
        total_bureaux = self.stats_bureaux['total']
        total_pv = pv_commune.count()
        
        return {
            'total_pv': total_pv,
            'pv_en_attente': pv_commune.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_commune.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_commune.filter(statut='REJETE').count(),
            'pv_en_correction': pv_commune.filter(statut='CORRECTION').count(),
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round(
                (pv_commune.filter(statut='VALIDE').count() / total_pv * 100), 2
            ) if total_pv > 0 else 0,
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation de la commune"""
        from  pv.models import ProcesVerbal
        
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune=self,
            statut='VALIDE'
        )
        
        total_inscrits = pv_valides.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        total_votants = pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0
        total_exprimes = pv_valides.aggregate(Sum('suffrages_exprimes'))['suffrages_exprimes__sum'] or 0
        total_nuls = pv_valides.aggregate(Sum('bulletins_nuls'))['bulletins_nuls__sum'] or 0
        total_blancs = pv_valides.aggregate(Sum('bulletins_blancs'))['bulletins_blancs__sum'] or 0
        
        return {
            'total_inscrits': total_inscrits,
            'total_votants': total_votants,
            'total_exprimes': total_exprimes,
            'total_nuls': total_nuls,
            'total_blancs': total_blancs,
            'taux_participation': round((total_votants / total_inscrits * 100), 2) if total_inscrits > 0 else 0,
            'taux_nuls': round((total_nuls / total_votants * 100), 2) if total_votants > 0 else 0,
            'taux_blancs': round((total_blancs / total_votants * 100), 2) if total_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents de la commune"""
        from  incidents.models import Incident
        
        incidents = Incident.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture__commune=self
        )
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour la commune"""
        from  pv.models import ResultatCandidat
        
        resultats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote__sous_prefecture__commune=self,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')
        
        total_voix = sum(r['total_voix'] for r in resultats)
        
        return [
            {
                'candidat': r['candidat__nom_complet'],
                'parti': r['candidat__parti_politique'],
                'numero': r['candidat__numero_ordre'],
                'voix': r['total_voix'],
                'pourcentage': round((r['total_voix'] / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    def get_stats_par_sous_prefecture(self):
        """Statistiques détaillées par sous-préfecture"""
        stats = []
        for sp in self.sous_prefectures.all():
            stats.append({
                'sous_prefecture': sp.nom_sous_prefecture,
                'code': sp.code_sous_prefecture,
                'bureaux': sp.stats_bureaux,
                'pv': sp.stats_pv,
                'participation': sp.stats_participation,
                'incidents': sp.stats_incidents,
            })
        return stats


class SousPrefecture(BaseGeoModel):
    """Sous-préfecture - Niveau 4"""
    commune = models.ForeignKey(
        Commune, 
        on_delete=models.CASCADE, 
        related_name='sous_prefectures'
    )
    code_sous_prefecture = models.CharField(
        max_length=10, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_sous_prefecture = models.CharField(max_length=200)
    
    # Métadonnées
    population = models.IntegerField(default=0)

    class Meta:
        db_table = 'geo_sous_prefectures'
        ordering = ['nom_sous_prefecture']
        verbose_name = 'Sous-préfecture'
        verbose_name_plural = 'Sous-préfectures'
        indexes = [
            models.Index(fields=['code_sous_prefecture']),
            models.Index(fields=['commune', 'nom_sous_prefecture']),
        ]

    def __str__(self):
        return f"{self.code_sous_prefecture} - {self.nom_sous_prefecture}"
    
    # ========== STATISTIQUES SOUS-PRÉFECTURE ==========
    
    @property
    def stats_bureaux(self):
        """Statistiques des bureaux de vote de la sous-préfecture"""
        from  geography.models import BureauVote
        
        bureaux = BureauVote.objects.filter(
            lieu_vote__sous_prefecture=self
        )
        
        return {
            'total': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'moyenne_inscrits': bureaux.aggregate(Avg('nombre_inscrits'))['nombre_inscrits__avg'] or 0,
        }
    
    @property
    def stats_pv(self):
        """Statistiques des PV de la sous-préfecture"""
        from  pv.models import ProcesVerbal
        
        pv_sp = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture=self
        )
        
        total_bureaux = self.stats_bureaux['total']
        total_pv = pv_sp.count()
        
        return {
            'total_pv': total_pv,
            'pv_en_attente': pv_sp.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_sp.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_sp.filter(statut='REJETE').count(),
            'pv_en_correction': pv_sp.filter(statut='CORRECTION').count(),
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round(
                (pv_sp.filter(statut='VALIDE').count() / total_pv * 100), 2
            ) if total_pv > 0 else 0,
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation de la sous-préfecture"""
        from  pv.models import ProcesVerbal
        
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture=self,
            statut='VALIDE'
        )
        
        total_inscrits = pv_valides.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        total_votants = pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0
        total_exprimes = pv_valides.aggregate(Sum('suffrages_exprimes'))['suffrages_exprimes__sum'] or 0
        total_nuls = pv_valides.aggregate(Sum('bulletins_nuls'))['bulletins_nuls__sum'] or 0
        total_blancs = pv_valides.aggregate(Sum('bulletins_blancs'))['bulletins_blancs__sum'] or 0
        
        return {
            'total_inscrits': total_inscrits,
            'total_votants': total_votants,
            'total_exprimes': total_exprimes,
            'total_nuls': total_nuls,
            'total_blancs': total_blancs,
            'taux_participation': round((total_votants / total_inscrits * 100), 2) if total_inscrits > 0 else 0,
            'taux_nuls': round((total_nuls / total_votants * 100), 2) if total_votants > 0 else 0,
            'taux_blancs': round((total_blancs / total_votants * 100), 2) if total_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents de la sous-préfecture"""
        from  incidents.models import Incident
        
        incidents = Incident.objects.filter(
            bureau_vote__lieu_vote__sous_prefecture=self
        )
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour la sous-préfecture"""
        from  pv.models import ResultatCandidat
        
        resultats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote__sous_prefecture=self,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')
        
        total_voix = sum(r['total_voix'] for r in resultats)
        
        return [
            {
                'candidat': r['candidat__nom_complet'],
                'parti': r['candidat__parti_politique'],
                'numero': r['candidat__numero_ordre'],
                'voix': r['total_voix'],
                'pourcentage': round((r['total_voix'] / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    def get_stats_par_lieu_vote(self):
        """Statistiques détaillées par lieu de vote"""
        stats = []
        for lv in self.lieux_vote.all():
            stats.append({
                'lieu_vote': lv.nom_lv,
                'code': lv.code_lv,
                'bureaux': lv.stats_bureaux,
                'pv': lv.stats_pv,
                'participation': lv.stats_participation,
                'incidents': lv.stats_incidents,
            })
        return stats


class LieuVote(BaseGeoModel):
    """Lieu de vote - Niveau 5"""
    sous_prefecture = models.ForeignKey(
        SousPrefecture, 
        on_delete=models.CASCADE, 
        related_name='lieux_vote'
    )
    code_lv = models.CharField(
        max_length=20, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_lv = models.CharField(max_length=200, verbose_name="Nom du lieu de vote")
    
    # Informations détaillées
    adresse = models.TextField(blank=True, null=True)
    type_lieu = models.CharField(
        max_length=50,
        choices=[
            ('ECOLE', 'École'),
            ('MAIRIE', 'Mairie'),
            ('CENTRE_COMMUNAUTAIRE', 'Centre communautaire'),
            ('SALLE_POLYVALENTE', 'Salle polyvalente'),
            ('AUTRE', 'Autre'),
        ],
        default='ECOLE'
    )
    
    # Géolocalisation
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        blank=True, 
        null=True,
        help_text="Latitude GPS"
    )
    longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=7, 
        blank=True, 
        null=True,
        help_text="Longitude GPS"
    )
    
    # Accessibilité
    est_accessible_pmr = models.BooleanField(
        default=False, 
        verbose_name="Accessible aux personnes à mobilité réduite"
    )
    
    # Capacité
    nombre_salles = models.IntegerField(default=1)

    class Meta:
        db_table = 'geo_lieux_vote'
        ordering = ['code_lv']
        verbose_name = 'Lieu de vote'
        verbose_name_plural = 'Lieux de vote'
        indexes = [
            models.Index(fields=['code_lv']),
            models.Index(fields=['sous_prefecture', 'nom_lv']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.code_lv} - {self.nom_lv}"
    
    @property
    def get_region(self):
        """Remonte jusqu'à la région"""
        return self.sous_prefecture.commune.departement.region
    
    @property
    def hierarchie_complete(self):
        """Retourne la hiérarchie complète"""
        return {
            'region': self.sous_prefecture.commune.departement.region,
            'departement': self.sous_prefecture.commune.departement,
            'commune': self.sous_prefecture.commune,
            'sous_prefecture': self.sous_prefecture,
            'lieu_vote': self
        }
    
    # ========== STATISTIQUES LIEU DE VOTE ==========
    
    @property
    def stats_bureaux(self):
        """Statistiques des bureaux de vote du lieu"""
        bureaux = self.bureaux_vote.all()
        
        return {
            'total': bureaux.count(),
            'total_inscrits': bureaux.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0,
            'moyenne_inscrits': bureaux.aggregate(Avg('nombre_inscrits'))['nombre_inscrits__avg'] or 0,
        }
    
    @property
    def stats_pv(self):
        """Statistiques des PV du lieu de vote"""
        from  pv.models import ProcesVerbal
        
        pv_lv = ProcesVerbal.objects.filter(bureau_vote__lieu_vote=self)
        
        total_bureaux = self.bureaux_vote.count()
        total_pv = pv_lv.count()
        
        return {
            'total_pv': total_pv,
            'pv_en_attente': pv_lv.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_lv.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_lv.filter(statut='REJETE').count(),
            'pv_en_correction': pv_lv.filter(statut='CORRECTION').count(),
            'taux_soumission': round((total_pv / total_bureaux * 100), 2) if total_bureaux > 0 else 0,
            'taux_validation': round(
                (pv_lv.filter(statut='VALIDE').count() / total_pv * 100), 2
            ) if total_pv > 0 else 0,
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation du lieu de vote"""
        from  pv.models import ProcesVerbal
        
        pv_valides = ProcesVerbal.objects.filter(
            bureau_vote__lieu_vote=self,
            statut='VALIDE'
        )
        
        total_inscrits = pv_valides.aggregate(Sum('nombre_inscrits'))['nombre_inscrits__sum'] or 0
        total_votants = pv_valides.aggregate(Sum('nombre_votants'))['nombre_votants__sum'] or 0
        total_exprimes = pv_valides.aggregate(Sum('suffrages_exprimes'))['suffrages_exprimes__sum'] or 0
        total_nuls = pv_valides.aggregate(Sum('bulletins_nuls'))['bulletins_nuls__sum'] or 0
        total_blancs = pv_valides.aggregate(Sum('bulletins_blancs'))['bulletins_blancs__sum'] or 0
        
        return {
            'total_inscrits': total_inscrits,
            'total_votants': total_votants,
            'total_exprimes': total_exprimes,
            'total_nuls': total_nuls,
            'total_blancs': total_blancs,
            'taux_participation': round((total_votants / total_inscrits * 100), 2) if total_inscrits > 0 else 0,
            'taux_nuls': round((total_nuls / total_votants * 100), 2) if total_votants > 0 else 0,
            'taux_blancs': round((total_blancs / total_votants * 100), 2) if total_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents du lieu de vote"""
        from  incidents.models import Incident
        
        incidents = Incident.objects.filter(bureau_vote__lieu_vote=self)
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour le lieu de vote"""
        from  pv.models import ResultatCandidat
        
        resultats = ResultatCandidat.objects.filter(
            proces_verbal__bureau_vote__lieu_vote=self,
            proces_verbal__statut='VALIDE'
        ).values(
            'candidat__nom_complet',
            'candidat__parti_politique',
            'candidat__numero_ordre'
        ).annotate(
            total_voix=Sum('nombre_voix')
        ).order_by('-total_voix')
        
        total_voix = sum(r['total_voix'] for r in resultats)
        
        return [
            {
                'candidat': r['candidat__nom_complet'],
                'parti': r['candidat__parti_politique'],
                'numero': r['candidat__numero_ordre'],
                'voix': r['total_voix'],
                'pourcentage': round((r['total_voix'] / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    def get_stats_par_bureau(self):
        """Statistiques détaillées par bureau de vote"""
        stats = []
        for bureau in self.bureaux_vote.all():
            stats.append({
                'bureau': bureau.nom_bv,
                'code': bureau.code_bv,
                'inscrits': bureau.nombre_inscrits,
                'pv': bureau.stats_pv,
                'participation': bureau.stats_participation,
                'incidents': bureau.stats_incidents,
            })
        return stats


class BureauVote(BaseGeoModel):
    """Bureau de vote - Niveau 6 (Final)"""
    lieu_vote = models.ForeignKey(
        LieuVote, 
        on_delete=models.CASCADE, 
        related_name='bureaux_vote'
    )
    code_bv = models.CharField(
        max_length=30, 
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9_-]+$', 'Code invalide')]
    )
    nom_bv = models.CharField(max_length=200, verbose_name="Nom du bureau de vote")
    
    # Données électorales de base
    nombre_inscrits = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Nombre d'électeurs inscrits"
    )
    
    # Organisation du bureau
    numero_ordre = models.IntegerField(
        default=1, 
        help_text="Numéro d'ordre dans le lieu de vote"
    )
    salle_numero = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Numéro ou nom de la salle"
    )
    
    # Statut opérationnel
    est_actif = models.BooleanField(default=True)
    commentaire = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'geo_bureaux_vote'
        ordering = ['lieu_vote', 'numero_ordre']
        verbose_name = 'Bureau de vote'
        verbose_name_plural = 'Bureaux de vote'
        unique_together = ['lieu_vote', 'numero_ordre']
        indexes = [
            models.Index(fields=['code_bv']),
            models.Index(fields=['lieu_vote', 'numero_ordre']),
            models.Index(fields=['est_actif']),
        ]

    def __str__(self):
        return f"{self.code_bv} - {self.nom_bv}"
    
    def clean(self):
        """Validation du modèle"""
        super().clean()
        if self.nombre_inscrits < 0:
            raise ValidationError("Le nombre d'inscrits ne peut pas être négatif")
    
    @property
    def get_region(self):
        """Remonte jusqu'à la région"""
        return self.lieu_vote.sous_prefecture.commune.departement.region
    
    @property
    def get_departement(self):
        """Récupère le département"""
        return self.lieu_vote.sous_prefecture.commune.departement
    
    @property
    def get_commune(self):
        """Récupère la commune"""
        return self.lieu_vote.sous_prefecture.commune
    
    @property
    def get_sous_prefecture(self):
        """Récupère la sous-préfecture"""
        return self.lieu_vote.sous_prefecture
    
    @property
    def hierarchie_complete(self):
        """Retourne la hiérarchie complète"""
        return {
            'region': self.get_region,
            'departement': self.get_departement,
            'commune': self.get_commune,
            'sous_prefecture': self.get_sous_prefecture,
            'lieu_vote': self.lieu_vote,
            'bureau_vote': self
        }
    
    # ========== STATISTIQUES BUREAU DE VOTE ==========
    
    @property
    def stats_pv(self):
        """Statistiques des PV du bureau"""
        from  pv.models import ProcesVerbal
        
        pv_bureau = self.proces_verbaux.all()
        
        return {
            'total_pv': pv_bureau.count(),
            'pv_en_attente': pv_bureau.filter(statut='EN_ATTENTE').count(),
            'pv_valides': pv_bureau.filter(statut='VALIDE').count(),
            'pv_rejetes': pv_bureau.filter(statut='REJETE').count(),
            'pv_en_correction': pv_bureau.filter(statut='CORRECTION').count(),
            'a_pv_valide': pv_bureau.filter(statut='VALIDE').exists(),
        }
    
    @property
    def stats_participation(self):
        """Statistiques de participation du bureau"""
        from  pv.models import ProcesVerbal
        
        pv_valide = self.proces_verbaux.filter(statut='VALIDE').first()
        
        if not pv_valide:
            return {
                'pv_disponible': False,
                'total_inscrits': self.nombre_inscrits,
                'total_votants': 0,
                'total_exprimes': 0,
                'total_nuls': 0,
                'total_blancs': 0,
                'taux_participation': 0,
                'taux_nuls': 0,
                'taux_blancs': 0,
            }
        
        return {
            'pv_disponible': True,
            'total_inscrits': pv_valide.nombre_inscrits,
            'total_votants': pv_valide.nombre_votants,
            'total_exprimes': pv_valide.suffrages_exprimes,
            'total_nuls': pv_valide.bulletins_nuls,
            'total_blancs': pv_valide.bulletins_blancs,
            'taux_participation': pv_valide.taux_participation,
            'taux_nuls': round(
                (pv_valide.bulletins_nuls / pv_valide.nombre_votants * 100), 2
            ) if pv_valide.nombre_votants > 0 else 0,
            'taux_blancs': round(
                (pv_valide.bulletins_blancs / pv_valide.nombre_votants * 100), 2
            ) if pv_valide.nombre_votants > 0 else 0,
        }
    
    @property
    def stats_incidents(self):
        """Statistiques des incidents du bureau"""
        incidents = self.incidents.all()
        
        return {
            'total': incidents.count(),
            'ouverts': incidents.filter(statut='OUVERT').count(),
            'en_cours': incidents.filter(statut='EN_COURS').count(),
            'traites': incidents.filter(statut='TRAITE').count(),
            'clos': incidents.filter(statut='CLOS').count(),
            'urgents': incidents.filter(priorite='URGENTE').count(),
            'par_categorie': dict(
                incidents.values('categorie').annotate(count=Count('id')).values_list('categorie', 'count')
            ),
        }
    
    @property
    def stats_resultats_candidats(self):
        """Résultats par candidat pour le bureau"""
        from  pv.models import ProcesVerbal
        
        pv_valide = self.proces_verbaux.filter(statut='VALIDE').first()
        
        if not pv_valide:
            return []
        
        resultats = pv_valide.resultats.select_related('candidat').order_by('-nombre_voix')
        
        total_voix = sum(r.nombre_voix for r in resultats)
        
        return [
            {
                'candidat': r.candidat.nom_complet,
                'parti': r.candidat.parti_politique,
                'numero': r.candidat.numero_ordre,
                'voix': r.nombre_voix,
                'pourcentage': round((r.nombre_voix / total_voix * 100), 2) if total_voix > 0 else 0
            }
            for r in resultats
        ]
    
    @property
    def pv_valide(self):
        """Retourne le PV validé s'il existe"""
        return self.proces_verbaux.filter(statut='VALIDE').first()
    
    @property
    def superviseur_actuel(self):
        """Retourne le superviseur actuellement en check-in"""
        from  accounts.models import CheckIn
        
        checkin_actif = CheckIn.objects.filter(
            bureau_vote=self,
            is_active=True,
            checkout_time__isnull=True
        ).select_related('superviseur').first()
        
        return checkin_actif.superviseur if checkin_actif else None
    
    @property
    def derniere_activite(self):
        """Date de la dernière activité sur ce bureau"""
        from django.db.models import Max
        
        dates = []
        
        # Dernier PV
        dernier_pv = self.proces_verbaux.aggregate(Max('date_soumission'))['date_soumission__max']
        if dernier_pv:
            dates.append(dernier_pv)
        
        # Dernier incident
        dernier_incident = self.incidents.aggregate(Max('created_at'))['created_at__max']
        if dernier_incident:
            dates.append(dernier_incident)
        
        # Dernier check-in
        dernier_checkin = self.checkins.aggregate(Max('checkin_time'))['checkin_time__max']
        if dernier_checkin:
            dates.append(dernier_checkin)
        
        return max(dates) if dates else None
    