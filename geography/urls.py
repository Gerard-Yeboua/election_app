# geography/urls.py
from django.urls import path
from . import views

app_name = 'geography'

urlpatterns = [
    path('upload/', views.upload_electoral_data, name='upload_data'),
]