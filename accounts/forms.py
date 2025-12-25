# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from accounts.models import User, CheckIn


class LoginForm(AuthenticationForm):
    """Formulaire de connexion"""
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Mot de passe'
        })
    )


class UserCreateForm(UserCreationForm):
    """Formulaire de création d'utilisateur"""
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'telephone', 'matricule',
            'role', 'region', 'departement', 'commune', 'sous_prefecture',
            'lieu_vote', 'bureau_vote', 'photo'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'class': 'form-input'}),
            'matricule': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'region': forms.Select(attrs={'class': 'form-select'}),
            'departement': forms.Select(attrs={'class': 'form-select'}),
            'commune': forms.Select(attrs={'class': 'form-select'}),
            'sous_prefecture': forms.Select(attrs={'class': 'form-select'}),
            'lieu_vote': forms.Select(attrs={'class': 'form-select'}),
            'bureau_vote': forms.Select(attrs={'class': 'form-select'}),
        }


class UserUpdateForm(forms.ModelForm):
    """Formulaire de modification d'utilisateur"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'telephone', 'matricule',
            'role', 'region', 'departement', 'commune', 'sous_prefecture',
            'lieu_vote', 'bureau_vote', 'photo', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'telephone': forms.TextInput(attrs={'class': 'form-input'}),
            'matricule': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'region': forms.Select(attrs={'class': 'form-select'}),
            'departement': forms.Select(attrs={'class': 'form-select'}),
            'commune': forms.Select(attrs={'class': 'form-select'}),
            'sous_prefecture': forms.Select(attrs={'class': 'form-select'}),
            'lieu_vote': forms.Select(attrs={'class': 'form-select'}),
            'bureau_vote': forms.Select(attrs={'class': 'form-select'}),
        }


class CheckInForm(forms.ModelForm):
    """Formulaire de check-in"""
    
    class Meta:
        model = CheckIn
        fields = ['nom_saisi', 'latitude', 'longitude', 'precision_gps']
        widgets = {
            'nom_saisi': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nom exact du bureau de vote'
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'precision_gps': forms.HiddenInput(),
        }