# apps/common/services/notification_service.py
"""
Service de notification via Supabase Realtime
"""
from supabase import create_client, Client
from django.conf import settings
import json


class NotificationService:
    """Service pour envoyer des notifications en temps réel"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    
    def notifier_nouveau_pv(self, pv):
        """Notifie les admins d'un nouveau PV"""
        notification = {
            'type': 'NOUVEAU_PV',
            'pv_id': str(pv.id),
            'numero_reference': pv.numero_reference,
            'bureau': pv.bureau_vote.code_bv,
            'superviseur': pv.superviseur.nom_complet,
            'has_incoherence': pv.has_incoherence,
            'timestamp': pv.date_soumission.isoformat()
        }
        
        # Publier sur le canal Supabase
        self.supabase.table('notifications').insert(notification).execute()
    
    def notifier_nouvel_incident(self, incident):
        """Notifie les admins d'un nouvel incident"""
        notification = {
            'type': 'NOUVEL_INCIDENT',
            'incident_id': str(incident.id),
            'numero_ticket': incident.numero_ticket,
            'bureau': incident.bureau_vote.code_bv,
            'categorie': incident.categorie,
            'priorite': incident.priorite,
            'superviseur': incident.superviseur.nom_complet,
            'timestamp': incident.created_at.isoformat()
        }
        
        self.supabase.table('notifications').insert(notification).execute()
    
    def notifier_changement_statut_pv(self, pv, ancien_statut, nouveau_statut):
        """Notifie le superviseur d'un changement de statut de son PV"""
        notification = {
            'type': 'CHANGEMENT_STATUT_PV',
            'destinataire_id': str(pv.superviseur.id),
            'pv_id': str(pv.id),
            'numero_reference': pv.numero_reference,
            'ancien_statut': ancien_statut,
            'nouveau_statut': nouveau_statut,
            'timestamp': pv.date_validation.isoformat() if pv.date_validation else None
        }
        
        self.supabase.table('notifications').insert(notification).execute()
    
    def notifier_nouveau_message_incident(self, message):
        """Notifie d'un nouveau message sur un incident"""
        # Déterminer le destinataire
        if message.auteur.role == 'SUPERVISEUR':
            # Message du superviseur → notifier l'admin
            destinataire = message.incident.admin_responsable
        else:
            # Message de l'admin → notifier le superviseur
            destinataire = message.incident.superviseur
        
        if not destinataire:
            return
        
        notification = {
            'type': 'NOUVEAU_MESSAGE_INCIDENT',
            'destinataire_id': str(destinataire.id),
            'incident_id': str(message.incident.id),
            'numero_ticket': message.incident.numero_ticket,
            'auteur': message.auteur.nom_complet,
            'message_id': str(message.id),
            'timestamp': message.created_at.isoformat()
        }
        
        self.supabase.table('notifications').insert(notification).execute()


# Instance globale
notification_service = NotificationService()