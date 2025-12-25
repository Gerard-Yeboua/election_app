from django.shortcuts import render

# Create your views here.
# apps/common/views.py
from django.shortcuts import render


def handler404(request, exception):
    """Page 404 personnalisée"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Page 500 personnalisée"""
    return render(request, 'errors/500.html', status=500)


def handler403(request, exception):
    """Page 403 personnalisée"""
    return render(request, 'errors/403.html', status=403)


def handler400(request, exception):
    """Page 400 personnalisée"""
    return render(request, 'errors/400.html', status=400)