# pv/services/pv_service.py
from django.db import transaction
from pv.models import ProcesVerbal, ResultatCandidat


class PVService:
    """Service de gestion des PV"""
    
    @transaction.atomic
    def creer_pv(self, bureau_vote, superviseur, data):
        """Créer un nouveau PV"""
        pv = ProcesVerbal.objects.create(
            bureau_vote=bureau_vote,
            superviseur=superviseur,
            **data
        )
        
        # Valider la cohérence automatiquement
        pv.validate_coherence()
        
        return pv
    
    @transaction.atomic
    def ajouter_resultats(self, pv, resultats_data):
        """Ajouter les résultats par candidat"""
        total_voix = 0
        
        for candidat_id, nombre_voix in resultats_data.items():
            ResultatCandidat.objects.create(
                pv=pv,
                candidat_id=candidat_id,
                nombre_voix=nombre_voix
            )
            total_voix += nombre_voix
        
        if total_voix != pv.suffrages_exprimes:
            raise ValueError(
                f"La somme des voix ({total_voix}) ne correspond pas "
                f"aux suffrages exprimés ({pv.suffrages_exprimes})"
            )
        
        pv.resultats_calcules = True
        pv.save()
        
        return pv


# Instance singleton - IMPORTANT !
pv_service = PVService()