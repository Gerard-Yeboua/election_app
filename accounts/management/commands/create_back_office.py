# accounts/management/commands/create_back_office.py
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from accounts.models import User


class Command(BaseCommand):
    help = 'Crée un utilisateur Back Office avec accès complet'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email du back office')
        parser.add_argument('--first-name', type=str, help='Prénom')
        parser.add_argument('--last-name', type=str, help='Nom')
        parser.add_argument('--password', type=str, help='Mot de passe')

    def handle(self, *args, **options):
        # Paramètres par défaut
        email = options.get('email') or 'backoffice@election.ci'
        first_name = options.get('first_name') or 'Back'
        last_name = options.get('last_name') or 'Office'
        password = options.get('password') or 'BackOffice@2025!'
        
        # Vérifier si l'utilisateur existe
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'❌ Utilisateur {email} existe déjà!'))
            return
        
        # Créer l'utilisateur BACK_OFFICE
        try:
            user = User.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='BACK_OFFICE',
                is_staff=True,
                is_superuser=True,
                is_active=True,
                password=make_password(password),
                # Pas d'affectation géographique pour BACK_OFFICE
                region=None,
                departement=None,
                commune=None,
                sous_prefecture=None,
                lieu_vote=None,
                bureau_vote=None
            )
            
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('✓ UTILISATEUR BACK OFFICE CRÉÉ AVEC SUCCÈS!'))
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Nom: {user.first_name} {user.last_name}')
            self.stdout.write(f'Role: {user.get_role_display()}')
            self.stdout.write(f'Périmètre: {user.perimetre_geographique}')
            self.stdout.write(f'Mot de passe: {password}')
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write(self.style.WARNING('\n⚠️  IMPORTANT: Changez le mot de passe après connexion!'))
            self.stdout.write(self.style.SUCCESS('\n✅ Cet utilisateur peut créer TOUS les admins et super admins!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erreur: {str(e)}'))
            import traceback
            traceback.print_exc()