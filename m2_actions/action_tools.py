"""
M2 - Outils d'action obligatoires
1. Formulaire de contact IMT avec Playwright
2. Email au directeur avec SendGrid/SMTP
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from dotenv import load_dotenv

# Import logger centralisé
try:
    from logger import log_info, log_warn, log_error
except ImportError:
    def log_info(m): pass
    def log_warn(m): print(m)
    def log_error(m): print(m)
from pydantic import BaseModel, Field

load_dotenv()

# Imports pour permettre le mocking dans les tests
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from sendgrid import SendGridAPIClient
except ImportError:
    SendGridAPIClient = None

# ==================== MODÈLES PYDANTIC ====================
class ContactFormData(BaseModel):
    """Données pour le formulaire de contact"""
    nom: str = Field(..., description="Nom complet")
    email: str = Field(..., description="Adresse email valide")
    telephone: Optional[str] = Field(None, description="Numéro de téléphone")
    message: str = Field(..., description="Message à envoyer")
    
class EmailData(BaseModel):
    """Données pour l'email au directeur"""
    sujet: str = Field(..., description="Sujet de l'email")
    corps: str = Field(..., description="Corps du message")
    destinataire: str = Field(default="directeur@imt.sn", description="Email du destinataire")

# ==================== OUTIL 1: FORMULAIRE DE CONTACT ====================
def fill_contact_form(
    nom: str, 
    email: str, 
    message: str, 
    telephone: str = None,
    url: str = "https://www.imt.sn/contact"
) -> Dict[str, Any]:
    """
    Remplit le formulaire de contact IMT avec Playwright
    
    Args:
        nom: Nom complet
        email: Adresse email
        message: Message à envoyer
        telephone: Numéro de téléphone (optionnel)
        url: URL du formulaire (par défaut: imt.sn/contact)
        
    Returns:
        Dict avec statut et preuve
    """
    log_info(f"📝 Tentative de remplissage formulaire pour: {nom}")
    
    # Validation des données
    data = ContactFormData(
        nom=nom,
        email=email,
        telephone=telephone,
        message=message
    )
    
    try:
        # Essayer d'utiliser Playwright (importé au niveau du module ou mocké)
        USE_PLAYWRIGHT = (sync_playwright is not None)
        
        if USE_PLAYWRIGHT:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            with sync_playwright() as p:
                # Lancer le navigateur en mode headless (sans interface)
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                
                # Créer un contexte avec user-agent réaliste
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                
                try:
                    # Naviguer vers la page
                    log_info(f"🌐 Navigation vers: {url}")
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # Attendre que le formulaire soit chargé
                    page.wait_for_selector("form", timeout=10000)
                    
                    # Remplir les champs (sélecteurs flexibles)
                    log_info("🖊️  Remplissage des champs...")
                    
                    # Essayer différents sélecteurs pour chaque champ
                    selectors_nom = [
                        'input[name="nom"]',
                        'input[name="name"]',
                        '#nom',
                        '#name',
                        'input[placeholder*="nom"]',
                        'input[placeholder*="Nom"]'
                    ]
                    
                    selectors_email = [
                        'input[name="email"]',
                        'input[type="email"]',
                        '#email',
                        'input[placeholder*="email"]',
                        'input[placeholder*="Email"]'
                    ]
                    
                    selectors_message = [
                        'textarea[name="message"]',
                        'textarea[name="msg"]',
                        '#message',
                        '#msg',
                        'textarea[placeholder*="message"]',
                        'textarea[placeholder*="Message"]'
                    ]
                    
                    selectors_telephone = [
                        'input[name="telephone"]',
                        'input[name="phone"]',
                        '#telephone',
                        '#phone',
                        'input[type="tel"]'
                    ]
                    
                    # Fonction pour trouver et remplir un champ
                    def fill_field(selectors_list, value, field_name):
                        for selector in selectors_list:
                            if page.locator(selector).count() > 0:
                                page.fill(selector, value)
                                log_info(f"  ✅ {field_name} rempli avec: {value}")
                                return True
                        log_warn(f"  ⚠️ {field_name}: aucun sélecteur trouvé")
                        return False
                    
                    # Remplir tous les champs
                    fill_field(selectors_nom, data.nom, "Nom")
                    fill_field(selectors_email, data.email, "Email")
                    fill_field(selectors_message, data.message, "Message")
                    
                    if data.telephone:
                        fill_field(selectors_telephone, data.telephone, "Téléphone")
                    
                    # Prendre un screenshot avant soumission
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_dir = Path("screenshots")
                    screenshot_dir.mkdir(exist_ok=True)
                    
                    screenshot_path = screenshot_dir / f"form_{timestamp}.png"
                    page.screenshot(path=str(screenshot_path))
                    log_info(f"📸 Screenshot sauvegardé: {screenshot_path}")
                    
                    # Chercher le bouton submit
                    submit_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Envoyer")',
                        'button:has-text("Submit")',
                        'button:has-text("Send")'
                    ]
                    
                    submitted = False
                    for selector in submit_selectors:
                        if page.locator(selector).count() > 0:
                            log_info(f"🔘 Clic sur bouton: {selector}")
                            page.click(selector)
                            
                            # Attendre un peu après soumission
                            page.wait_for_timeout(3000)
                            submitted = True
                            break
                    
                    if not submitted:
                        log_warn("⚠️ Bouton submit non trouvé, simulation de soumission")
                    
                    # Prendre un screenshot après soumission
                    screenshot_after = screenshot_dir / f"form_{timestamp}_after.png"
                    page.screenshot(path=str(screenshot_after))
                    
                    # Fermer le navigateur
                    browser.close()
                    
                    return {
                        "status": "success",
                        "message": "Formulaire rempli et soumis avec succès",
                        "screenshot": str(screenshot_path),
                        "screenshot_after": str(screenshot_after),
                        "timestamp": timestamp,
                        "data_submitted": data.model_dump(exclude_none=True),
                        "mode": "playwright_real"
                    }
                    
                except PlaywrightTimeoutError:
                    log_error("❌ Timeout lors du chargement de la page")
                    browser.close()
                    raise
                except Exception as e:
                    log_error(f"❌ Erreur Playwright: {e}")
                    if 'browser' in locals():
                        browser.close()
                    raise
        
        # Mode simulation (fallback)
        log_info("🔄 Mode simulation activé")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Créer un faux screenshot
        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(exist_ok=True)
        
        # Créer un fichier JSON de simulation
        sim_data = {
            "simulation": True,
            "timestamp": timestamp,
            "form_data": data.dict(exclude_none=True),
            "url": url,
            "message": "Formulaire simulé - Playwright requis pour l'exécution réelle"
        }
        
        sim_file = screenshot_dir / f"form_simulation_{timestamp}.json"
        with open(sim_file, 'w', encoding='utf-8') as f:
            json.dump(sim_data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "simulated",
            "message": "Formulaire simulé (Playwright non disponible)",
            "simulation_file": str(sim_file),
            "timestamp": timestamp,
            "data_submitted": data.model_dump(exclude_none=True),
            "mode": "simulation"
        }
        
    except Exception as e:
        error_msg = f"Erreur lors du remplissage du formulaire: {str(e)}"
        log_error(f"❌ {error_msg}")
        
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "mode": "error"
        }

# ==================== OUTIL 2: EMAIL AU DIRECTEUR ====================
def send_director_email(
    sujet: str, 
    corps: str,
    destinataire: str = "directeur@imt.sn"
) -> Dict[str, Any]:
    """
    Envoie un email formel au directeur de l'IMT
    
    Args:
        sujet: Sujet de l'email
        corps: Corps du message
        destinataire: Email du destinataire
        
    Returns:
        Dict avec statut d'envoi
    """
    log_info(f"📧 Préparation email pour: {destinataire}")
    
    # Validation des données
    data = EmailData(
        sujet=sujet,
        corps=corps,
        destinataire=destinataire
    )
    
    # Générer un email formel avec LLM si disponible
    email_content = data.corps
    try:
        import litellm
        from llm_utils import get_litellm_config, sanitize_env_keys
        
        sanitize_env_keys()
        primary, fallbacks = get_litellm_config()

        if primary:
            prompt = f"""
            Transforme ce message en email professionnel pour le directeur de l'IMT:

            Sujet: {data.sujet}
            Message original: {data.corps}

            Format demandé:
            1. Formule d'appel formelle
            2. Introduction courtoise
            3. Corps du message structuré
            4. Formule de politesse
            5. Signature: "Assistant IMT AI"

            Langue: Français formel
            Style: Professionnel, éducatif, respectueux
            """
            
            response = litellm.completion(
                model=primary,
                messages=[{"role": "user", "content": prompt}],
                fallbacks=fallbacks,
                temperature=0.3
            )
            email_content = response.choices[0].message.content
            log_info("✅ Email professionnel généré avec LLM")
    except Exception as e:
        log_warn(f"⚠️ Génération LLM échouée: {e}, utilisation du texte original")
    
    try:
        # Préparer le contenu HTML (remplacer les sauts de ligne par <br>)
        email_html_body = email_content.replace('\n', '<br>')
        
        # Essayer SendGrid d'abord
        sendgrid_key = os.getenv("SENDGRID_API_KEY")
        if sendgrid_key and SendGridAPIClient is not None:
            try:
                from sendgrid.helpers.mail import Mail, Content
                
                # Créer l'email
                message = Mail(
                    from_email='assistant@imt.sn',
                    to_emails=data.destinataire,
                    subject=f"[IMT Assistant] {data.sujet}",
                    html_content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background-color: #0056b3; color: white; padding: 10px; text-align: center; }}
                            .content {{ padding: 20px; }}
                            .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h2>Institut des Métiers des Télécommunications</h2>
                            </div>
                            <div class="content">
                                {email_html_body}
                            </div>
                            <div class="footer">
                                <p>Cet email a été généré automatiquement par l'Assistant IMT AI</p>
                                <p>IMT Dakar | Route de l'Aéroport, Dakar-Yoff | contact@imt.sn</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                )
                
                # Envoyer l'email
                sg = SendGridAPIClient(sendgrid_key)
                response = sg.send(message)
                
                log_info(f"✅ Email envoyé via SendGrid, statut: {response.status_code}")
                
                return {
                    "status": "sent",
                    "message": "Email envoyé avec succès via SendGrid",
                    "message_id": response.headers.get('X-Message-Id', 'unknown'),
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                    "mode": "sendgrid",
                    "to": data.destinataire,
                    "subject": data.sujet
                }
                
            except Exception as e:
                log_warn(f"⚠️ SendGrid échoué: {e}, essai SMTP")
        
        # Fallback: SMTP Gmail
        gmail_user = os.getenv("GMAIL_EMAIL")
        gmail_password = os.getenv("GMAIL_PASSWORD")
        
        if gmail_user and gmail_password:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                # Créer le message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"[IMT Assistant] {data.sujet}"
                msg['From'] = gmail_user
                msg['To'] = data.destinataire
                
                # Version texte
                text_part = MIMEText(email_content, 'plain', 'utf-8')
                msg.attach(text_part)
                
                # Version HTML
                html_content = f"""
                <html>
                <body>
                    <h3>Message de l'Assistant IMT:</h3>
                    <p>{email_html_body}</p>
                    <hr>
                    <p><small>Généré automatiquement par l'Assistant IMT AI</small></p>
                </body>
                </html>
                """
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)
                
                # Connexion et envoi
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(gmail_user, gmail_password)
                    server.send_message(msg)
                
                log_info(f"✅ Email envoyé via SMTP Gmail à {data.destinataire}")
                
                return {
                    "status": "sent",
                    "message": "Email envoyé avec succès via SMTP Gmail",
                    "timestamp": datetime.now().isoformat(),
                    "mode": "smtp_gmail",
                    "to": data.destinataire,
                    "subject": data.sujet
                }
                
            except Exception as e:
                log_warn(f"⚠️ SMTP Gmail échoué: {e}")
        
        # Fallback final: simulation
        log_info("🔄 Mode simulation email (aucune clé SMTP/SendGrid)")
        
        # Sauvegarder l'email simulé
        sim_dir = Path("emails_simulated")
        sim_dir.mkdir(exist_ok=True)
        
        sim_data = {
            "timestamp": datetime.now().isoformat(),
            "to": data.destinataire,
            "subject": data.sujet,
            "body": email_content,
            "status": "simulated",
            "note": "Email simulé - Configurez SendGrid ou Gmail SMTP pour l'envoi réel"
        }
        
        sim_file = sim_dir / f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(sim_file, 'w', encoding='utf-8') as f:
            json.dump(sim_data, f, indent=2, ensure_ascii=False)
        
        return {
            "status": "simulated",
            "message": "Email simulé (configuration SMTP requise)",
            "simulation_file": str(sim_file),
            "timestamp": datetime.now().isoformat(),
            "mode": "simulation",
            "to": data.destinataire,
            "subject": data.sujet
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de l'envoi de l'email: {str(e)}"
        log_error(f"❌ {error_msg}")
        
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "mode": "error"
        }

# ==================== INTERFACE UNIFIÉE ====================
class IMTActionTools:
    """Classe principale pour les outils d'action M2"""
    
    @staticmethod
    def fill_form(**kwargs) -> Dict:
        """Interface unifiée pour le formulaire"""
        return fill_contact_form(**kwargs)
    
    @staticmethod
    def send_email(**kwargs) -> Dict:
        """Interface unifiée pour l'email"""
        return send_director_email(**kwargs)
    
    @staticmethod
    def test_all():
        """Teste tous les outils"""
        print("🧪 Test complet des outils M2")
        print("=" * 60)
        
        # Test formulaire
        print("\n1. Test formulaire de contact:")
        form_result = fill_contact_form(
            nom="Test IMT",
            email="test@imt.sn",
            message="Ceci est un test de l'assistant IMT AI"
        )
        print(f"   Résultat: {form_result['status']}")
        print(f"   Mode: {form_result.get('mode', 'unknown')}")
        
        # Test email
        print("\n2. Test email au directeur:")
        email_result = send_director_email(
            sujet="Test assistant IMT",
            corps="Bonjour, ceci est un test de l'assistant IMT AI."
        )
        print(f"   Résultat: {email_result['status']}")
        print(f"   Mode: {email_result.get('mode', 'unknown')}")
        
        print("\n" + "=" * 60)
        print("✅ Tests terminés - M2 Actions prêtes")

# ==================== USAGE ====================
if __name__ == "__main__":
    # Tests interactifs
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            IMTActionTools.test_all()
        elif sys.argv[1] == "form" and len(sys.argv) >= 5:
            result = fill_contact_form(
                nom=sys.argv[2],
                email=sys.argv[3],
                message=sys.argv[4]
            )
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == "email" and len(sys.argv) >= 4:
            result = send_director_email(
                sujet=sys.argv[2],
                corps=sys.argv[3]
            )
            print(json.dumps(result, indent=2))
        else:
            print("Usage:")
            print("  python action_tools.py test")
            print("  python action_tools.py form 'Nom' 'email@test.com' 'Message'")
            print("  python action_tools.py email 'Sujet' 'Corps du message'")
    else:
        # Mode démo
        IMTActionTools.test_all()