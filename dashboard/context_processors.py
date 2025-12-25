# apps/dashboard/context_processors.py
from django.utils import timezone
from pv.models import ProcesVerbal
from incidents.models import Incident


def sidebar_context(request):
    """Context processor pour la sidebar"""
    context = {
        'current_year': timezone.now().year,
        'pv_en_attente_count': 0,
        'incidents_ouverts_count': 0,
        'notifications_count': 0,
    }
    
    if request.user.is_authenticated:
        if request.user.role in ['ADMIN', 'SUPER_ADMIN']:
            # Compter les PV en attente
            bureaux = request.user.get_bureaux_accessibles()
            context['pv_en_attente_count'] = ProcesVerbal.objects.filter(
                bureau_vote__in=bureaux,
                statut='EN_ATTENTE'
            ).count()
            
            # Compter les incidents ouverts
            context['incidents_ouverts_count'] = Incident.objects.filter(
                bureau_vote__in=bureaux,
                statut='OUVERT'
            ).count()
        
        # Notifications (à implémenter avec Supabase)
        context['notifications_count'] = 0
    
    return context