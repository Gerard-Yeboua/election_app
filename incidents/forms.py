# apps/incidents/forms.py
from django import forms
from .models import Incident, IncidentMessage, IncidentPhoto
from accounts.models import User


class IncidentForm(forms.ModelForm):
    """Formulaire de création d'incident"""
    
    class Meta:
        model = Incident
        fields = [
            'categorie', 'titre', 'description', 'heure_incident',
            'impact', 'vote_affecte', 'nombre_electeurs_impactes',
            'latitude', 'longitude'
        ]
        
        widgets = {
            'categorie': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }),
            'titre': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': 'Titre de l\'incident...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'rows': 5,
                'placeholder': 'Description détaillée de l\'incident (minimum 20 caractères)...'
            }),
            'heure_incident': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }),
            'impact': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }),
            'vote_affecte': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 focus:ring-primary-500'
            }),
            'nombre_electeurs_impactes': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput()
        }


class IncidentMessageForm(forms.ModelForm):
    """Formulaire de message d'incident"""
    
    class Meta:
        model = IncidentMessage
        fields = ['message', 'est_interne']
        
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'rows': 3,
                'placeholder': 'Votre message...'
            }),
            'est_interne': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-primary-600 focus:ring-primary-500'
            })
        }


class IncidentTraitementForm(forms.Form):
    """Formulaire de traitement d'incident"""
    
    ACTION_CHOICES = [
        ('attribuer', 'M\'attribuer'),
        ('demarrer', 'Démarrer traitement'),
        ('resoudre', 'Résoudre'),
        ('cloturer', 'Clôturer'),
        ('escalader', 'Escalader')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'text-primary-600 focus:ring-primary-500'
        })
    )
    
    solution = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
            'rows': 4,
            'placeholder': 'Description de la solution...'
        })
    )
    
    actions_menees = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
            'rows': 3,
            'placeholder': 'Actions menées...'
        })
    )
    
    escalade_vers = forms.ModelChoiceField(
        queryset=User.objects.filter(role='SUPER_ADMIN'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
        })
    )
    
    motif_escalade = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
            'rows': 3,
            'placeholder': 'Motif de l\'escalade...'
        })
    )


class IncidentPhotoForm(forms.ModelForm):
    """Formulaire d'ajout de photo"""
    
    class Meta:
        model = IncidentPhoto
        fields = ['photo', 'type_photo', 'legende']
        
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/*'
            }),
            'type_photo': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }),
            'legende': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': 'Légende de la photo...'
            })
        }