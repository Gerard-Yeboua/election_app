# Dans tests/test_permissions.py
from django.test import TestCase
from accounts.models import User
from geography.models import Region, Departement, Commune, SousPrefecture, LieuVote, BureauVote

class UserPermissionsTestCase(TestCase):
    """Tests des permissions utilisateur"""
    
    def setUp(self):
        """Créer les données de test"""
        # Créer une hiérarchie géographique
        self.region = Region.objects.create(
            code_region='01',
            nom_region='Test Region'
        )
        
        self.departement = Departement.objects.create(
            code_departement='01',
            nom_departement='Test Dept',
            region=self.region
        )
        
        self.commune = Commune.objects.create(
            code_commune='01',
            nom_commune='Test Commune',
            departement=self.departement
        )
        
        self.sous_prefecture = SousPrefecture.objects.create(
            code_sous_prefecture='01',
            nom_sous_prefecture='Test SP',
            commune=self.commune
        )
        
        self.lieu_vote = LieuVote.objects.create(
            code_lv='LV01',
            nom_lv='Test Lieu Vote',
            sous_prefecture=self.sous_prefecture
        )
        
        self.bureau_vote = BureauVote.objects.create(
            code_bv='BV01',
            lieu_vote=self.lieu_vote
        )
        
        # Créer les utilisateurs
        self.back_office = User.objects.create_user(
            email='backoffice@test.com',
            password='test123',
            first_name='Back',
            last_name='Office',
            role='BACK_OFFICE'
        )
        
        self.super_admin = User.objects.create_user(
            email='superadmin@test.com',
            password='test123',
            first_name='Super',
            last_name='Admin',
            role='SUPER_ADMIN',
            region=self.region
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            region=self.region
        )
        
        self.superviseur = User.objects.create_user(
            email='superviseur@test.com',
            password='test123',
            first_name='Super',
            last_name='Viseur',
            role='SUPERVISEUR',
            bureau_vote=self.bureau_vote
        )
    
    def test_back_office_acces_complet(self):
        """Le back office doit avoir accès à tout"""
        self.assertTrue(self.back_office.a_acces_complet())
        self.assertTrue(self.back_office.peut_voir_region(self.region))
        self.assertTrue(self.back_office.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.back_office.peut_creer_utilisateur())
        self.assertTrue(self.back_office.peut_valider_pv())
        self.assertTrue(self.back_office.peut_exporter_rapports())
        self.assertTrue(self.back_office.peut_gerer_parametres_systeme())
    
    def test_super_admin_acces_region(self):
        """Le super admin a accès à sa région"""
        self.assertFalse(self.super_admin.a_acces_complet())
        self.assertTrue(self.super_admin.peut_voir_region(self.region))
        self.assertTrue(self.super_admin.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.super_admin.peut_creer_utilisateur())
        self.assertFalse(self.super_admin.peut_gerer_parametres_systeme())
    
    def test_admin_acces_limite(self):
        """L'admin a un accès limité"""
        self.assertFalse(self.admin.a_acces_complet())
        self.assertTrue(self.admin.peut_voir_region(self.region))
        self.assertTrue(self.admin.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.admin.peut_creer_utilisateur())
        self.assertFalse(self.admin.peut_gerer_parametres_systeme())
    
    def test_superviseur_acces_bureau_uniquement(self):
        """Le superviseur n'a accès qu'à son bureau"""
        self.assertFalse(self.superviseur.a_acces_complet())
        self.assertTrue(self.superviseur.peut_voir_bureau(self.bureau_vote))
        self.assertFalse(self.superviseur.peut_creer_utilisateur())
        self.assertFalse(self.superviseur.peut_valider_pv())
    
    def test_get_incidents_accessibles(self):
        """Test des incidents accessibles selon le rôle"""
        # Le back office voit tout
        back_office_incidents = self.back_office.get_incidents_accessibles()
        self.assertIsNotNone(back_office_incidents)
        
        # Le superviseur voit uniquement son bureau
        superviseur_incidents = self.superviseur.get_incidents_accessibles()
        self.assertIsNotNone(superviseur_incidents)
    
    def test_modification_utilisateur(self):
        """Test des permissions de modification"""
        # Back office peut tout modifier
        self.assertTrue(self.back_office.peut_modifier_utilisateur(self.super_admin))
        self.assertTrue(self.back_office.peut_modifier_utilisateur(self.superviseur))
        
        # Super admin peut modifier dans sa région
        self.assertTrue(self.super_admin.peut_modifier_utilisateur(self.admin))
        self.assertTrue(self.super_admin.peut_modifier_utilisateur(self.superviseur))
        
        # Superviseur ne peut rien modifier
        self.assertFalse(self.superviseur.peut_modifier_utilisateur(self.admin))
    
    def test_suppression_utilisateur(self):
        """Test des permissions de suppression"""
        # Back office peut tout supprimer
        self.assertTrue(self.back_office.peut_supprimer_utilisateur(self.super_admin))
        
        # Super admin ne peut pas supprimer un autre super admin
        self.assertFalse(self.super_admin.peut_supprimer_utilisateur(self.back_office))
        
        # Superviseur ne peut rien supprimer
        self.assertFalse(self.superviseur.peut_supprimer_utilisateur(self.admin))


# Lancer les tests avec:
# python manage.py test accounts.tests.test_permissions