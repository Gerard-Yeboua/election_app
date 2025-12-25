# apps/incidents/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Incident, IncidentMessage, HistoriqueIncident
from accounts.models import AuditLog


@receiver(post_save, sender=Incident)
def incident_post_save(sender, instance, created, **kwargs):
    """Actions après la sauvegarde d'un incident"""
    
    if created:
        # Créer l'entrée dans l'historique
        HistoriqueIncident.objects.create(
            incident=instance,
            utilisateur=instance.superviseur,
            action='CREATION',
            nouveau_statut=instance.statut,
            commentaire=f"Incident créé: {instance.titre}"
        )
        
        # Log d'audit
        AuditLog.log(
            user=instance.superviseur,
            action='INCIDENT_CREATE',
            description=f"Création de l'incident {instance.numero_ticket}",
            target_model='Incident',
            target_id=str(instance.id),
            details={
                'categorie': instance.categorie,
                'priorite': instance.priorite,
                'bureau': instance.bureau_vote.code_bv
            }
        )
        
        # TODO: Notifier les admins via Supabase Realtime
        from .notifications import notifier_nouvel_incident
        notifier_nouvel_incident(instance)


@receiver(pre_save, sender=Incident)
def incident_pre_save(sender, instance, **kwargs):
    """Actions avant la sauvegarde d'un incident"""
    
    if instance.pk:
        try:
            ancien_incident = Incident.objects.get(pk=instance.pk)
            
            # Détecter les changements de statut
            if ancien_incident.statut != instance.statut:
                # TODO: Notifier via Supabase Realtime
                pass
            
            # Détecter les changements de priorité
            if ancien_incident.priorite != instance.priorite:
                HistoriqueIncident.objects.create(
                    incident=instance,
                    utilisateur=instance.admin_responsable or instance.superviseur,
                    action='CHANGEMENT_PRIORITE',
                    ancienne_priorite=ancien_incident.priorite,
                    nouvelle_priorite=instance.priorite
                )
        except Incident.DoesNotExist:
            pass


@receiver(post_save, sender=IncidentMessage)
def incident_message_post_save(sender, instance, created, **kwargs):
    """Actions après l'ajout d'un message"""
    
    if created:
        # Créer une entrée dans l'historique
        HistoriqueIncident.objects.create(
            incident=instance.incident,
            utilisateur=instance.auteur,
            action='AJOUT_MESSAGE',
            commentaire=f"Message ajouté par {instance.auteur.nom_complet}"
        )
        
        # TODO: Notifier le destinataire via Supabase Realtime
        from .notifications import notifier_nouveau_message
        notifier_nouveau_message(instance)
        