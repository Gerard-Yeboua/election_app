# Dans un fichier mixins.py ou permissions.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

class BackOfficeRequiredMixin(UserPassesTestMixin):
    """Nécessite un rôle Back Office"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'BACK_OFFICE'
    
    def handle_no_permission(self):
        raise PermissionDenied("Accès réservé au Back Office")


class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Nécessite un rôle Super Admin ou supérieur"""
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.role in ['BACK_OFFICE', 'SUPER_ADMIN']
        )


class AdminRequiredMixin(UserPassesTestMixin):
    """Nécessite un rôle Admin ou supérieur"""
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.role in ['BACK_OFFICE', 'SUPER_ADMIN', 'ADMIN']
        )


class SuperviseurRequiredMixin(UserPassesTestMixin):
    """Nécessite d'être authentifié (tous les rôles)"""
    
    def test_func(self):
        return self.request.user.is_authenticated


class BureauAccessMixin:
    """Mixin pour vérifier l'accès à un bureau de vote"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        bureau_id = kwargs.get('bureau_id') or kwargs.get('pk')
        if bureau_id:
            from geography.models import BureauVote
            try:
                bureau = BureauVote.objects.get(pk=bureau_id)
                if not request.user.peut_voir_bureau(bureau):
                    raise PermissionDenied("Vous n'avez pas accès à ce bureau de vote")
            except BureauVote.DoesNotExist:
                raise PermissionDenied("Bureau de vote introuvable")
        
        return super().dispatch(request, *args, **kwargs)


# Décorateurs pour les vues basées sur des fonctions
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def back_office_required(view_func):
    """Décorateur pour restreindre l'accès au Back Office"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'BACK_OFFICE':
            messages.error(request, "Accès réservé au Back Office")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Décorateur pour restreindre l'accès aux admins"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role not in ['BACK_OFFICE', 'SUPER_ADMIN', 'ADMIN']:
            messages.error(request, "Accès réservé aux administrateurs")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# Exemple d'utilisation dans une vue

# Vue basée sur une classe
from django.views.generic import ListView
from incidents.models import Incident

class IncidentListView(AdminRequiredMixin, ListView):
    model = Incident
    template_name = 'incidents/list.html'
    
    def get_queryset(self):
        # Le back office voit tout, les autres voient selon leur périmètre
        return self.request.user.get_incidents_accessibles()


# Vue basée sur une fonction
@admin_required
def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    
    # Vérifier l'accès
    if not request.user.peut_voir_bureau(incident.bureau_vote):
        raise PermissionDenied("Vous n'avez pas accès à cet incident")
    
    return render(request, 'incidents/detail.html', {'incident': incident})