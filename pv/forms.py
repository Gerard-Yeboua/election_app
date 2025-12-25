# apps/pv/forms.py
from django import forms
from django.forms import inlineformset_factory
from pv.models import ProcesVerbal, ResultatCandidat, Candidat


class ProcesVerbalForm(forms.ModelForm):
    """Formulaire de soumission de PV"""
    
    class Meta:
        model = ProcesVerbal
        fields = '__all__'
        
        widgets = {
            'nombre_inscrits': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'nombre_votants': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'suffrages_exprimes': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'bulletins_nuls': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'bulletins_blancs': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'placeholder': '0',
                'min': '0'
            }),
            'photo_pv_officiel': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/*'
            }),
            'photo_tableau_resultats': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/*'
            }),
            'photo_bureau_1': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/*'
            }),
            'photo_bureau_2': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/*'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'precision_gps': forms.HiddenInput(),
            'observations': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
                'rows': 3,
                'placeholder': 'Observations éventuelles...'
            })
        }


class ResultatCandidatForm(forms.ModelForm):
    """Formulaire pour un résultat de candidat"""
    
    class Meta:
        model = ResultatCandidat
        fields = ['candidat', 'nombre_voix']
        widgets = {
            'candidat': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500'
            }),
            'nombre_voix': forms.NumberInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500 text-center text-lg font-semibold',
                'placeholder': '0',
                'min': '0'
            })
        }


# Formset pour les résultats
ResultatCandidatFormSet = inlineformset_factory(
    ProcesVerbal,
    ResultatCandidat,
    form=ResultatCandidatForm,
    extra=0,
    can_delete=False
)


class ValidationForm(forms.Form):
    """Formulaire de validation de PV"""
    
    ACTION_CHOICES = [
        ('valider', 'Valider'),
        ('rejeter', 'Rejeter'),
        ('correction', 'Demander correction')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'text-primary-600 focus:ring-primary-500'
        })
    )
    
    motif_rejet = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-red-500 focus:ring-red-500',
            'rows': 4,
            'placeholder': 'Motif du rejet (obligatoire si rejet)...'
        })
    )
    
    commentaires = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500',
            'rows': 3,
            'placeholder': 'Commentaires additionnels...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        motif_rejet = cleaned_data.get('motif_rejet')
        
        if action == 'rejeter' and not motif_rejet:
            raise forms.ValidationError("Le motif de rejet est obligatoire")
        
        return cleaned_data