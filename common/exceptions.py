# apps/common/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Handler d'exceptions personnalisé pour DRF"""
    
    # Appeler le handler par défaut
    response = exception_handler(exc, context)
    
    if response is not None:
        # Personnaliser la réponse
        custom_response = {
            'error': True,
            'message': str(exc),
            'details': response.data if isinstance(response.data, dict) else {'detail': response.data}
        }
        
        response.data = custom_response
    
    return response
