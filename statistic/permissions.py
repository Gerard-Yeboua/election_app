# apps/statistics/permissions.py
from rest_framework import permissions


class CanViewStatistics(permissions.BasePermission):
    """
    Permission pour voir les statistiques
    Tous les utilisateurs authentifiés peuvent voir les stats de leur périmètre
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanViewNationalStatistics(permissions.BasePermission):
    """
    Permission pour voir les statistiques nationales
    Réservé aux Super Admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )


class CanRefreshCache(permissions.BasePermission):
    """
    Permission pour rafraîchir le cache
    Réservé aux Admins et Super Admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['ADMIN', 'SUPER_ADMIN']
        )


class CanManageCache(permissions.BasePermission):
    """
    Permission pour gérer le cache (invalidation, suppression)
    Réservé aux Super Admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'SUPER_ADMIN' or request.user.is_superuser)
        )


class HasScopeAccess(permissions.BasePermission):
    """
    Vérifie que l'utilisateur a accès au périmètre demandé
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super Admin a accès à tout
        if request.user.role == 'SUPER_ADMIN':
            return True
        
        # Vérifier le périmètre demandé
        region_id = view.kwargs.get('region_id') or request.query_params.get('region_id')
        bureau_id = view.kwargs.get('bureau_id') or request.query_params.get('bureau_id')
        
        if region_id and request.user.region:
            return str(request.user.region.id) == str(region_id)
        
        if bureau_id and request.user.bureau_vote:
            return str(request.user.bureau_vote.id) == str(bureau_id)
        
        return True