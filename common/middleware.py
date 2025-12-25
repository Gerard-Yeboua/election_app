# apps/common/middleware.py
from django.utils import timezone
from accounts.models import AuditLog


class AuditMiddleware:
    """Middleware pour logger les actions importantes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Logger les actions POST importantes
        if request.method == 'POST' and request.user.is_authenticated:
            path = request.path
            
            # Définir les chemins à logger
            paths_to_log = [
                '/pv/submit/',
                '/pv/validate/',
                '/incidents/create/',
                '/accounts/users/create/',
            ]
            
            if any(path.startswith(p) for p in paths_to_log):
                AuditLog.log(
                    user=request.user,
                    action='HTTP_POST',
                    description=f"POST request to {path}",
                    ip_address=self.get_client_ip(request)
                )
        
        return response
    
    def get_client_ip(self, request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    