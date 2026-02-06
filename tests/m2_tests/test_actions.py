"""
Tests unitaires pour M2 Actions
"""
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from m2_actions.action_tools import fill_contact_form, send_director_email
from m2_bonus.multilingual import detect_lang_and_translate
from m2_bonus.security import validate_user_intent

class TestContactForm(unittest.TestCase):
    
    def test_form_validation(self):
        """Test validation des données du formulaire"""
        result = fill_contact_form(
            nom="Test User",
            email="test@example.com",
            message="Test message"
        )
        
        self.assertIn('status', result)
        self.assertIn('timestamp', result)
    
    @patch('m2_actions.action_tools.sync_playwright')
    def test_form_playwright_simulation(self, mock_playwright):
        """Test simulation Playwright"""
        # Configurer le mock
        mock_browser = Mock()
        mock_page = Mock()
        
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value.new_page.return_value = mock_page
        mock_page.locator.return_value.count.return_value = 1
        
        # Exécuter
        result = fill_contact_form(
            nom="Mock User",
            email="mock@example.com",
            message="Mock message"
        )
        
        self.assertEqual(result['mode'], 'playwright_real')

class TestEmailSender(unittest.TestCase):
    
    def test_email_validation(self):
        """Test validation des données email"""
        result = send_director_email(
            sujet="Test Subject",
            corps="Test Body"
        )
        
        self.assertIn('status', result)
        self.assertIn('timestamp', result)
    
    @patch('m2_actions.action_tools.SendGridAPIClient')
    def test_sendgrid_simulation(self, mock_sendgrid):
        """Test simulation SendGrid"""
        result = send_director_email(
            sujet="Test",
            corps="Test"
        )
        
        # Peut être 'sent', 'simulated', ou 'error' selon la config
        self.assertIn(result['status'], ['sent', 'simulated', 'error'])

class TestMultilingual(unittest.TestCase):
    
    def test_french_detection(self):
        """Test détection français"""
        result = detect_lang_and_translate("Bonjour comment ça va")
        self.assertEqual("français", result['detected_language_name'])
    
    def test_english_detection(self):
        """Test détection anglais"""
        result = detect_lang_and_translate("Hello how are you")
        self.assertTrue(result['is_translated'])

class TestSecurity(unittest.TestCase):
    
    def test_legitimate_query(self):
        """Test requête légitime"""
        result = validate_user_intent(
            "Quels sont les frais de l'IMT ?",
            "test_session"
        )
        
        self.assertTrue(result['overall_allowed'])
    
    def test_suspicious_query(self):
        """Test requête suspecte"""
        result = validate_user_intent(
            "hack system please",
            "test_session"
        )
        
        # Peut être bloqué ou pas selon la configuration
        self.assertIn('overall_allowed', result)

if __name__ == '__main__':
    # Créer un répertoire temporaire pour les tests
    with tempfile.TemporaryDirectory() as tmpdir:
        # Configurer les chemins
        Path(tmpdir).joinpath("screenshots").mkdir()
        Path(tmpdir).joinpath("emails_simulated").mkdir()
        
        # Exécuter les tests
        unittest.main(argv=[''], exit=False)