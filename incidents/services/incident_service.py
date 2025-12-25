# incidents/services/incident_service.py
from django.db import transaction
from django.utils import timezone
from incidents.models import Incident, IncidentMessage, HistoriqueIncident


class IncidentService:
    """Service de gestion des incidents"""
    
    @transaction.atomic
    def creer_incident(self, bureau_vote, superviseur, data):
        """Créer un nouvel incident"""
        incident = Incident.objects.create(
            bureau_vote=bureau_vote,
            superviseur=superviseur,
            **data
        )
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='CREER',
            utilisateur=superviseur,
            description=f"Incident créé: {incident.titre}"
        )
        
        return incident
    
    @transaction.atomic
    def attribuer_incident(self, incident, admin):
        """Attribuer un incident à un admin"""
        incident.admin_responsable = admin
        incident.date_attribution = timezone.now()
        incident.save()
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='ATTRIBUER',
            utilisateur=admin,
            description=f"Incident attribué à {admin.nom_complet}"
        )
        
        return incident
    
    @transaction.atomic
    def demarrer_traitement(self, incident, admin):
        """Démarrer le traitement d'un incident"""
        incident.statut = 'EN_COURS'
        incident.date_debut_traitement = timezone.now()
        incident.save()
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='DEMARRER',
            utilisateur=admin,
            description="Traitement démarré"
        )
        
        return incident
    
    @transaction.atomic
    def resoudre_incident(self, incident, admin, solution, actions_menees=None):
        """Résoudre un incident"""
        if not solution:
            raise ValueError("La solution est obligatoire")
        
        incident.statut = 'TRAITE'
        incident.date_resolution = timezone.now()
        incident.solution = solution
        incident.actions_menees = actions_menees
        
        if incident.created_at and incident.date_resolution:
            delta = incident.date_resolution - incident.created_at
            incident.temps_resolution = delta.total_seconds() / 60
        
        incident.save()
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='RESOUDRE',
            utilisateur=admin,
            description=f"Incident résolu: {solution[:100]}"
        )
        
        return incident
    
    @transaction.atomic
    def cloturer_incident(self, incident, admin):
        """Clôturer un incident"""
        incident.statut = 'CLOS'
        incident.date_cloture = timezone.now()
        incident.save()
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='CLOTURER',
            utilisateur=admin,
            description="Incident clôturé"
        )
        
        return incident
    
    @transaction.atomic
    def escalader_incident(self, incident, admin, escalade_vers, motif_escalade):
        """Escalader un incident"""
        if not escalade_vers or not motif_escalade:
            raise ValueError("L'admin cible et le motif sont obligatoires")
        
        incident.admin_responsable = escalade_vers
        incident.escalade = True
        incident.date_escalade = timezone.now()
        incident.motif_escalade = motif_escalade
        incident.save()
        
        HistoriqueIncident.objects.create(
            incident=incident,
            action='ESCALADER',
            utilisateur=admin,
            description=f"Escaladé vers {escalade_vers.nom_complet}: {motif_escalade}"
        )
        
        return incident
    
    @transaction.atomic
    def ajouter_message(self, incident, auteur, message, est_interne=False):
        """Ajouter un message à l'incident"""
        msg = IncidentMessage.objects.create(
            incident=incident,
            auteur=auteur,
            message=message,
            est_interne=est_interne
        )
        
        return msg


# Instance singleton - IMPORTANT !
incident_service = IncidentService()