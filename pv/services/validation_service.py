# pv/services/validation_service.py
from django.db import transaction
from django.utils import timezone
from pv.models import ProcesVerbal, HistoriqueValidation


class ValidationService:
    """Service de validation des PV"""
    
    @transaction.atomic
    def valider_pv(self, pv, validateur, commentaires=None):
        """Valider un PV"""
        pv.statut = 'VALIDE'
        pv.date_validation = timezone.now()
        pv.validateur = validateur
        pv.commentaires_validation = commentaires
        
        if pv.date_soumission and pv.date_validation:
            delta = pv.date_validation - pv.date_soumission
            pv.delai_validation = delta.total_seconds() / 3600
        
        pv.save()
        
        HistoriqueValidation.objects.create(
            pv=pv,
            action='VALIDER',
            validateur=validateur,
            commentaire=commentaires or ''
        )
        
        return pv
    
    @transaction.atomic
    def rejeter_pv(self, pv, validateur, motif_rejet, commentaires=None):
        """Rejeter un PV"""
        if not motif_rejet:
            raise ValueError("Le motif de rejet est obligatoire")
        
        pv.statut = 'REJETE'
        pv.date_validation = timezone.now()
        pv.validateur = validateur
        pv.motif_rejet = motif_rejet
        pv.commentaires_validation = commentaires
        pv.save()
        
        HistoriqueValidation.objects.create(
            pv=pv,
            action='REJETER',
            validateur=validateur,
            motif_rejet=motif_rejet,
            commentaire=commentaires or ''
        )
        
        return pv
    
    @transaction.atomic
    def demander_correction(self, pv, validateur, commentaires):
        """Demander une correction"""
        pv.statut = 'EN_ATTENTE'
        pv.commentaires_validation = commentaires
        pv.save()
        
        HistoriqueValidation.objects.create(
            pv=pv,
            action='CORRECTION',
            validateur=validateur,
            commentaire=commentaires or ''
        )
        
        return pv


# Instance singleton - IMPORTANT !
validation_service = ValidationService()