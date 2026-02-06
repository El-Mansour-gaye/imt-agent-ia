"""
M2 - Playwright Form Automation
Remplissage automatisé du formulaire de contact IMT avec screenshot proof
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def fill_imt_contact_form(
    nom: str, 
    email: str, 
    message: str,
    telephone: str = None,
    url: str = "https://www.imt.sn/contact",
    screenshot_dir: str = "screenshots"
) -> Dict[str, Any]:
    """
    Remplit et soumet le formulaire de contact IMT via Playwright
    
    Args:
        nom: Nom complet de l'utilisateur
        email: Adresse email
        message: Message à envoyer
        telephone: Numéro de téléphone (optionnel)
        url: URL du formulaire
        screenshot_dir: Répertoire pour sauvegarder les screenshots
        
    Returns:
        Dict avec status, proof_path, timestamp, logs
    """
    print(f"📝 Remplissage formulaire IMT: {nom} <{email}>")
    
    # Créer le répertoire de screenshots s'il n'existe pas
    Path(screenshot_dir).mkdir(exist_ok=True)
    
    logs = []
    timestamp = datetime.now().isoformat()
    screenshot_path = None
    
    try:
        with sync_playwright() as p:
            # Lancer navigateur avec user-agent réaliste
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            logs.append(f"[{timestamp}] ✅ Navigateur lancé")
            
            try:
                # Navigation
                print(f"🌐 Accès: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                logs.append(f"[{timestamp}] ✅ Page chargée: {url}")
                
                # Attendre le formulaire
                page.wait_for_selector("form", timeout=10000)
                logs.append(f"[{timestamp}] ✅ Formulaire détecté")
                
                # Remplir les champs avec détection de sélecteurs flexibles
                print("🖊️  Remplissage des champs...")
                
                # Champ nom - essayer plusieurs sélecteurs
                nom_selectors = ["input[name='name']", "input[name='nom']", "input#name", "input[placeholder*='nom']"]
                for selector in nom_selectors:
                    try:
                        if page.query_selector(selector):
                            page.fill(selector, nom)
                            logs.append(f"[{timestamp}] ✅ Nom rempli: {selector}")
                            break
                    except:
                        continue
                
                # Champ email
                email_selectors = ["input[name='email']", "input[type='email']", "input#email"]
                for selector in email_selectors:
                    try:
                        if page.query_selector(selector):
                            page.fill(selector, email)
                            logs.append(f"[{timestamp}] ✅ Email rempli: {selector}")
                            break
                    except:
                        continue
                
                # Champ téléphone (optionnel)
                if telephone:
                    phone_selectors = ["input[name='phone']", "input[name='telephone']", "input[type='tel']"]
                    for selector in phone_selectors:
                        try:
                            if page.query_selector(selector):
                                page.fill(selector, telephone)
                                logs.append(f"[{timestamp}] ✅ Téléphone rempli: {selector}")
                                break
                        except:
                            continue
                
                # Champ message
                message_selectors = ["textarea[name='message']", "textarea#message", "textarea"]
                for selector in message_selectors:
                    try:
                        if page.query_selector(selector):
                            page.fill(selector, message)
                            logs.append(f"[{timestamp}] ✅ Message rempli: {selector}")
                            break
                    except:
                        continue
                
                # Soumettre le formulaire
                print("📤 Soumission du formulaire...")
                submit_selectors = ["button[type='submit']", "input[type='submit']", "button:has-text('Envoyer')", "button:has-text('Submit')"]
                for selector in submit_selectors:
                    try:
                        if page.query_selector(selector):
                            page.click(selector)
                            page.wait_for_timeout(2000)  # Attendre la soumission
                            logs.append(f"[{timestamp}] ✅ Formulaire soumis: {selector}")
                            break
                    except:
                        continue
                
                # Screenshot de confirmation
                screenshot_file = f"{screenshot_dir}/contact_form_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_file)
                screenshot_path = screenshot_file
                logs.append(f"[{timestamp}] ✅ Screenshot sauvegardé: {screenshot_file}")
                
                print(f"✅ Formulaire soumis avec succès!")
                
                return {
                    "status": "success",
                    "message": "Formulaire rempli et soumis",
                    "nom": nom,
                    "email": email,
                    "telephone": telephone,
                    "screenshot_path": screenshot_path,
                    "timestamp": timestamp,
                    "logs": logs
                }
                
            except PlaywrightTimeoutError as e:
                logs.append(f"[{timestamp}] ❌ Timeout: {str(e)}")
                raise
            finally:
                context.close()
                browser.close()
                
    except Exception as e:
        error_msg = f"❌ Erreur formulaire: {str(e)}"
        logs.append(f"[{timestamp}] {error_msg}")
        print(error_msg)
        
        return {
            "status": "error",
            "message": error_msg,
            "nom": nom,
            "email": email,
            "telephone": telephone,
            "screenshot_path": None,
            "timestamp": timestamp,
            "logs": logs
        }


class PlaywrightFormHandler:
    """Handle form interactions using Playwright (backward compatibility)"""
    
    def __init__(self):
        self.browser = None
        self.page = None
    
    async def initialize(self):
        """Initialize Playwright browser"""
        from playwright.async_api import async_playwright
        p = await async_playwright().start()
        self.browser = await p.chromium.launch()
        self.page = await self.browser.new_page()
    
    async def fill_form(self, url: str, form_data: Dict[str, str]) -> bool:
        """Fill and submit a form"""
        try:
            await self.page.goto(url)
            
            for field_name, field_value in form_data.items():
                await self.page.fill(f"input[name='{field_name}']", field_value)
            
            await self.page.click("button[type='submit']")
            return True
        except Exception as e:
            print(f"Form filling error: {str(e)}")
            return False
    
    async def extract_form_fields(self, url: str) -> List[str]:
        """Extract all form fields from a page"""
        try:
            await self.page.goto(url)
            fields = await self.page.query_selector_all("input")
            return [await f.get_attribute("name") for f in fields]
        except Exception as e:
            print(f"Form extraction error: {str(e)}")
            return []
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
