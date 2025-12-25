# apps/common/signals.py
from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_default_data(sender, **kwargs):
    """Créer des données par défaut après migration"""
    
    if sender.name == 'apps.pv':
        # Créer des candidats par défaut si la table est vide
        Candidat = apps.get_model('pv', 'Candidat')
        
        if not Candidat.objects.exists():
            print("Création des candidats par défaut...")
            # Vous pouvez ajouter vos candidats par défaut ici
    
    if sender.name == 'apps.incidents':
        # Créer des modèles d'incidents par défaut
        ModeleIncident = apps.get_model('incidents', 'ModeleIncident')
        
        if not ModeleIncident.objects.exists():
            print("Création des modèles d'incidents par défaut...")
            modeles = [
                {
                    'nom': 'Absence d\'assesseurs',
                    'categorie': 'ABSENCE_ASSESSEURS',
                    'titre_template': 'Absence d\'assesseurs',
                    'description_template': 'Un ou plusieurs assesseurs sont absents du bureau de vote.',
                    'priorite_defaut': 'HAUTE',
                    'impact_defaut': 'ELEVE'
                },
                {
                    'nom': 'Matériel manquant',
                    'categorie': 'MATERIEL_MANQUANT',
                    'titre_template': 'Matériel électoral manquant',
                    'description_template': 'Du matériel électoral nécessaire au bon déroulement du vote est manquant.',
                    'priorite_defaut': 'HAUTE',
                    'impact_defaut': 'ELEVE'
                },
                # Ajoutez d'autres modèles...
            ]
            
            for modele in modeles:
                ModeleIncident.objects.create(**modele)
                