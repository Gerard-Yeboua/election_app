# accounts/tests/test_permissions.py
from django.test import TestCase
from accounts.models import User
from geography.models import Region, Departement, Commune, SousPrefecture, LieuVote, BureauVote


class UserPermissionsTestCase(TestCase):
    """Tests des permissions utilisateur"""
    
    def setUp(self):
        """Créer les données de test"""
        # Créer une hiérarchie géographique
        self.region = Region.objects.create(
            code_region='TEST01',
            nom_region='Test Region'
        )
        
        self.departement = Departement.objects.create(
            code_departement='TESTDEPT01',
            nom_departement='Test Dept',
            region=self.region
        )
        
        self.commune = Commune.objects.create(
            code_commune='TESTCOM01',
            nom_commune='Test Commune',
            departement=self.departement
        )
        
        self.sous_prefecture = SousPrefecture.objects.create(
            code_sous_prefecture='TESTSP01',
            nom_sous_prefecture='Test SP',
            commune=self.commune
        )
        
        self.lieu_vote = LieuVote.objects.create(
            code_lv='TESTLV01',
            nom_lv='Test Lieu Vote',
            sous_prefecture=self.sous_prefecture
        )
        
        self.bureau_vote = BureauVote.objects.create(
            code_bv='TESTBV01',
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
        print("\n🧪 Test: Back office - Accès complet")
        
        self.assertTrue(self.back_office.a_acces_complet())
        self.assertTrue(self.back_office.peut_voir_region(self.region))
        self.assertTrue(self.back_office.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.back_office.peut_creer_utilisateur())
        self.assertTrue(self.back_office.peut_valider_pv())
        self.assertTrue(self.back_office.peut_exporter_rapports())
        self.assertTrue(self.back_office.peut_gerer_parametres_systeme())
        
        print("✅ Back office a tous les accès")
    
    def test_super_admin_acces_region(self):
        """Le super admin a accès à sa région"""
        print("\n🧪 Test: Super Admin - Accès région")
        
        self.assertFalse(self.super_admin.a_acces_complet())
        self.assertTrue(self.super_admin.peut_voir_region(self.region))
        self.assertTrue(self.super_admin.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.super_admin.peut_creer_utilisateur())
        self.assertFalse(self.super_admin.peut_gerer_parametres_systeme())
        
        print("✅ Super Admin a accès à sa région uniquement")
    
    def test_admin_acces_limite(self):
        """L'admin a un accès limité"""
        print("\n🧪 Test: Admin - Accès limité")
        
        self.assertFalse(self.admin.a_acces_complet())
        self.assertTrue(self.admin.peut_voir_region(self.region))
        self.assertTrue(self.admin.peut_voir_bureau(self.bureau_vote))
        self.assertTrue(self.admin.peut_creer_utilisateur())
        self.assertFalse(self.admin.peut_gerer_parametres_systeme())
        
        print("✅ Admin a un accès limité")
    
    def test_superviseur_acces_bureau_uniquement(self):
        """Le superviseur n'a accès qu'à son bureau"""
        print("\n🧪 Test: Superviseur - Bureau uniquement")
        
        self.assertFalse(self.superviseur.a_acces_complet())
        self.assertTrue(self.superviseur.peut_voir_bureau(self.bureau_vote))
        self.assertFalse(self.superviseur.peut_creer_utilisateur())
        self.assertFalse(self.superviseur.peut_valider_pv())
        
        print("✅ Superviseur accède uniquement à son bureau")
    
    def test_get_incidents_accessibles(self):
        """Test des incidents accessibles selon le rôle"""
        print("\n🧪 Test: Incidents accessibles")
        
        # Le back office voit tout
        back_office_incidents = self.back_office.get_incidents_accessibles()
        self.assertIsNotNone(back_office_incidents)
        
        # Le superviseur voit uniquement son bureau
        superviseur_incidents = self.superviseur.get_incidents_accessibles()
        self.assertIsNotNone(superviseur_incidents)
        
        print("✅ Requêtes d'incidents fonctionnent correctement")
    
    def test_get_bureaux_vote_accessibles(self):
        """Test des bureaux de vote accessibles"""
        print("\n🧪 Test: Bureaux de vote accessibles")
        
        # Back office voit tous les bureaux
        bureaux_back_office = self.back_office.get_bureaux_vote_accessibles()
        self.assertTrue(bureaux_back_office.filter(pk=self.bureau_vote.pk).exists())
        
        # Superviseur voit uniquement son bureau
        bureaux_superviseur = self.superviseur.get_bureaux_vote_accessibles()
        self.assertEqual(bureaux_superviseur.count(), 1)
        self.assertEqual(bureaux_superviseur.first(), self.bureau_vote)
        
        print("✅ Accès aux bureaux de vote fonctionnent")
    
    def test_modification_utilisateur(self):
        """Test des permissions de modification"""
        print("\n🧪 Test: Modification d'utilisateurs")
        
        # Back office peut tout modifier
        self.assertTrue(self.back_office.peut_modifier_utilisateur(self.super_admin))
        self.assertTrue(self.back_office.peut_modifier_utilisateur(self.superviseur))
        
        # Super admin peut modifier dans sa région
        self.assertTrue(self.super_admin.peut_modifier_utilisateur(self.admin))
        self.assertTrue(self.super_admin.peut_modifier_utilisateur(self.superviseur))
        
        # Superviseur ne peut rien modifier
        self.assertFalse(self.superviseur.peut_modifier_utilisateur(self.admin))
        
        print("✅ Permissions de modification correctes")
    
    def test_suppression_utilisateur(self):
        """Test des permissions de suppression"""
        print("\n🧪 Test: Suppression d'utilisateurs")
        
        # Back office peut tout supprimer
        self.assertTrue(self.back_office.peut_supprimer_utilisateur(self.super_admin))
        
        # Super admin ne peut pas supprimer un autre super admin
        self.assertFalse(self.super_admin.peut_supprimer_utilisateur(self.back_office))
        
        # Superviseur ne peut rien supprimer
        self.assertFalse(self.superviseur.peut_supprimer_utilisateur(self.admin))
        
        print("✅ Permissions de suppression correctes")
    
    def test_perimetre_geographique(self):
        """Test du périmètre géographique"""
        print("\n🧪 Test: Périmètre géographique")
        
        self.assertEqual(self.back_office.perimetre_geographique, "National - Accès complet")
        self.assertIn("Région", self.super_admin.perimetre_geographique)
        self.assertIn("Bureau", self.superviseur.perimetre_geographique)
        
        print("✅ Périmètres géographiques corrects")
    
    def test_roles_properties(self):
        """Test des propriétés de rôles"""
        print("\n🧪 Test: Propriétés de rôles")
        
        # Back office
        self.assertTrue(self.back_office.est_back_office)
        self.assertFalse(self.back_office.est_superviseur)
        
        # Super admin
        self.assertTrue(self.super_admin.est_super_admin)
        self.assertFalse(self.super_admin.est_superviseur)
        
        # Admin
        self.assertTrue(self.admin.est_admin)
        self.assertFalse(self.admin.est_superviseur)
        
        # Superviseur
        self.assertTrue(self.superviseur.est_superviseur)
        self.assertFalse(self.superviseur.est_admin)
        
        print("✅ Propriétés de rôles correctes")


class UserCreationTestCase(TestCase):
    """Tests de création d'utilisateurs"""
    
    def test_create_back_office(self):
        """Test création utilisateur back office"""
        print("\n🧪 Test: Création Back Office")
        
        user = User.objects.create_user(
            email='test@backoffice.com',
            password='test123',
            first_name='Test',
            last_name='User',
            role='BACK_OFFICE'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'BACK_OFFICE')
        self.assertTrue(user.a_acces_complet())
        
        print("✅ Back office créé avec succès")
    
    def test_username_auto_generation(self):
        """Test génération automatique du username"""
        print("\n🧪 Test: Génération username")
        
        user = User.objects.create_user(
            email='test.user@example.com',
            password='test123',
            first_name='Test',
            last_name='User',
            role='BACK_OFFICE'
        )
        
        self.assertEqual(user.username, 'test.user')
        
        print("✅ Username généré automatiquement")


print("\n" + "="*70)
print("🚀 TESTS DES PERMISSIONS UTILISATEUR")
print("="*70)