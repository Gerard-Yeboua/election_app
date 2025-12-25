# scripts/init_db.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from geography.models import Region, Departement, Commune
from pv.models import Candidat

User = get_user_model()

def create_superuser():
    """Créer un superutilisateur"""
    if not User.objects.filter(email='admin@cei.ci').exists():
        User.objects.create_superuser(
            email='admin@cei.ci',
            password='Admin@123',
            first_name='Admin',
            last_name='CEI',
            role='SUPER_ADMIN'
        )
        print("✓ Superutilisateur créé")

def create_test_data():
    """Créer des données de test"""
    # Créer une région
    region, created = Region.objects.get_or_create(
        code_region='CI-01',
        defaults={'nom_region': 'Abidjan'}
    )
    if created:
        print("✓ Région Abidjan créée")
    
    # Créer des candidats de test
    candidats = [
        {'numero_ordre': 1, 'nom_complet': 'Candidat A', 'parti_politique': 'Parti Alpha'},
        {'numero_ordre': 2, 'nom_complet': 'Candidat B', 'parti_politique': 'Parti Beta'},
        {'numero_ordre': 3, 'nom_complet': 'Candidat C', 'parti_politique': 'Parti Gamma'},
    ]
    
    for candidat_data in candidats:
        Candidat.objects.get_or_create(**candidat_data)
    
    print("✓ Candidats de test créés")

if __name__ == '__main__':
    print("Initialisation de la base de données...")
    create_superuser()
    create_test_data()
    print("\n✓ Initialisation terminée!")
    print("\nConnexion admin:")
    print("  Email: admin@cei.ci")
    print("  Password: Admin@123")