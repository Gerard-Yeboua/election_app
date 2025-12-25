# apps/accounts/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from .models import User, CheckIn, AuditLog, LoginHistory


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Actions après la sauvegarde d'un utilisateur"""
    
    if created:
        # Log de création
        AuditLog.log(
            user=instance.created_by,
            action='USER_CREATE',
            description=f"Création de l'utilisateur {instance.nom_complet}",
            target_model='User',
            target_id=str(instance.id),
            details={
                'email': instance.email,
                'role': instance.role,
                'perimetre': instance.perimetre_geographique
            }
        )
    else:
        # Log de modification
        AuditLog.log(
            user=instance,
            action='USER_UPDATE',
            description=f"Modification de l'utilisateur {instance.nom_complet}",
            target_model='User',
            target_id=str(instance.id)
        )


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Actions lors de la connexion d'un utilisateur"""
    
    # Incrémenter le compteur de connexions
    user.login_count += 1
    user.last_login_ip = get_client_ip(request)
    user.save(update_fields=['login_count', 'last_login_ip'])
    
    # Créer un historique de connexion
    LoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        success=True
    )
    
    # Log d'audit
    AuditLog.log(
        user=user,
        action='LOGIN',
        description=f"Connexion de {user.nom_complet}",
        ip_address=get_client_ip(request)
    )


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Actions lors de la déconnexion d'un utilisateur"""
    
    if user:
        # Mettre à jour le dernier historique de connexion
        last_login = LoginHistory.objects.filter(
            user=user,
            logout_time__isnull=True
        ).order_by('-login_time').first()
        
        if last_login:
            last_login.logout_time = timezone.now()
            last_login.save()
        
        # Log d'audit
        AuditLog.log(
            user=user,
            action='LOGOUT',
            description=f"Déconnexion de {user.nom_complet}",
            ip_address=get_client_ip(request) if request else None
        )


@receiver(post_save, sender=CheckIn)
def checkin_post_save(sender, instance, created, **kwargs):
    """Actions après un check-in"""
    
    if created:
        # Log d'audit
        AuditLog.log(
            user=instance.superviseur,
            action='CHECKIN',
            description=f"Check-in au bureau {instance.bureau_vote.code_bv}",
            target_model='CheckIn',
            target_id=str(instance.id),
            details={
                'bureau': instance.bureau_vote.code_bv,
                'latitude': str(instance.latitude),
                'longitude': str(instance.longitude)
            }
        )


def get_client_ip(request):
    """Récupère l'IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
