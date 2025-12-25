# accounts/services/check_in_service.py
from django.db import transaction
from django.utils import timezone
from accounts.models import CheckIn
from common.utils import calculate_distance


class CheckInService:
    """Service de gestion des check-ins"""
    
    @transaction.atomic
    def effectuer_checkin(self, superviseur, bureau_vote, nom_saisi, latitude, longitude, precision_gps=None):
        """Effectuer un check-in"""
        # Vérifier le nom du bureau
        if nom_saisi.strip().lower() != bureau_vote.nom_bv.strip().lower():
            raise ValueError("Le nom du bureau saisi ne correspond pas")
        
        # Vérifier la distance si GPS disponible
        if latitude and longitude and bureau_vote.latitude and bureau_vote.longitude:
            distance = calculate_distance(
                latitude, longitude,
                bureau_vote.latitude, bureau_vote.longitude
            )
            
            # Alerte si distance > 500m
            if distance > 500:
                raise ValueError(
                    f"Vous êtes trop éloigné du bureau ({distance:.0f}m). "
                    "Le check-in doit être effectué sur place."
                )
        
        # Créer le check-in
        checkin = CheckIn.objects.create(
            superviseur=superviseur,
            bureau_vote=bureau_vote,
            nom_saisi=nom_saisi,
            latitude=latitude,
            longitude=longitude,
            precision_gps=precision_gps,
            checkin_time=timezone.now()
        )
        
        return checkin
    
    @transaction.atomic
    def effectuer_checkout(self, checkin):
        """Effectuer un check-out"""
        checkin.checkout_time = timezone.now()
        
        # Calculer la durée
        if checkin.checkin_time and checkin.checkout_time:
            delta = checkin.checkout_time - checkin.checkin_time
            checkin.duree_minutes = delta.total_seconds() / 60
        
        checkin.save()
        
        return checkin


# Instance singleton
check_in_service = CheckInService()