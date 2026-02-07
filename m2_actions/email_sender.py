"""
M2 - Email Sender
Génération et envoi d'emails au directeur IMT via SendGrid/SMTP
"""
import os
import smtplib
from datetime import datetime
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()


class DirectorEmailGenerator:
    """Générateur d'emails formels au directeur IMT"""
    
    DIRECTOR_EMAIL = "directeur@imt.sn"
    EMAIL_TEMPLATE = """
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2E75B6; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #ddd; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 20px; text-align: center; }}
                .signature {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Institut Mines-Télécom de Dakar</h2>
                </div>
                <div class="content">
                    <p>Madame, Monsieur le Directeur,</p>
                    {body}
                    {signature}
                </div>
                <div class="footer">
                    <p>Email généré automatiquement le {timestamp}</p>
                    <p>Institut Mines-Télécom de Dakar | www.imt.sn</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    def __init__(self):
        self.use_sendgrid = bool(os.getenv("SENDGRID_API_KEY"))
        self.use_smtp = bool(os.getenv("GMAIL_EMAIL")) and bool(os.getenv("GMAIL_PASSWORD"))
        
    def generate_formal_email(
        self, 
        user_request: str, 
        user_name: str = "Utilisateur",
        context: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        Génère un email formel au directeur basé sur la demande utilisateur
        
        Args:
            user_request: Demande/question de l'utilisateur
            user_name: Nom de l'utilisateur
            context: Contexte additionnel (ex: frais, formation)
            
        Returns:
            Dict avec subject, body, to_email
        """
        # Tentative avec LLM (Gemini avec fallback Grok via LiteLLM)
        try:
            import litellm
            gemini_key = os.getenv("GEMINI_API_KEY")
            xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            primary = f"gemini/{model_name.replace('gemini/', '')}"

            fallbacks = ["gemini/gemini-1.5-flash"]
            if xai_key:
                grok_model = os.getenv("GROK_MODEL") or "grok-2-latest"
                fallbacks.append(f"xai/{grok_model.replace('xai/', '')}")

            prompt = f"""En tant qu'Assistant IA Officiel de l'IMT Dakar, rédigez un email institutionnel
            exemplaire destiné au Directeur de l'IMT.
            
            DÉTAILS DE LA REQUÊTE :
            - Objet de la demande : {user_request}
            - Identité de l'étudiant/prospect : {user_name}
            - Contexte additionnel : {context or 'Demande d'information générale'}
            
            EXIGENCES :
            1. TON : Formel, respectueux, académique et courtois.
            2. STRUCTURE :
               - Salutations distinguées.
               - Présentation claire de la demande.
               - Argumentation succincte si nécessaire.
               - Formule de politesse finale.
            3. LONGUEUR : Concis mais complet (max 250 mots).
            4. LANGUE : Français soutenu.
            
            FORMAT DE RÉPONSE ATTENDU (STRICT) :
            SUJET : [Sujet clair et explicite]
            CORPS : [Contenu de l'email]"""
            
            response = litellm.completion(
                model=primary,
                messages=[{"role": "user", "content": prompt}],
                fallbacks=fallbacks,
                temperature=0.5
            )
            email_content = response.choices[0].message.content
            
            # Parser la réponse
            parts = email_content.split("CORPS:")
            subject_part = parts[0].replace("SUJET:", "").strip()
            body_part = parts[1].strip() if len(parts) > 1 else user_request
            
        except Exception as e:
            print(f"⚠️ Gemini non disponible ({e}), utilisation template simple")
            subject_part = f"Demande d'information: {user_request[:50]}..."
            body_part = user_request
        
        # Formatter le corps
        formatted_body = f"""
        <p>Je vous contacte concernant la demande suivante:</p>
        <p><strong>{body_part}</strong></p>
        <p>Pouvez-vous nous aider avec cette question?</p>
        """
        
        signature = f"""
        <div class="signature">
            <p>Cordialement,<br/>
            {user_name}<br/>
            Utilisateur IMT Assistant</p>
        </div>
        """
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        html_body = self.EMAIL_TEMPLATE.format(
            body=formatted_body,
            signature=signature,
            timestamp=timestamp
        )
        
        return {
            "subject": subject_part,
            "body": html_body,
            "plain_text": body_part,
            "to_email": self.DIRECTOR_EMAIL,
            "from_email": os.getenv("GMAIL_EMAIL", "noreply@imt.sn")
        }


class EmailSender:
    """Envoyeur d'emails avec SendGrid ou SMTP"""
    
    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.gmail_email = os.getenv("GMAIL_EMAIL")
        self.gmail_password = os.getenv("GMAIL_PASSWORD")
        self.logs: List[str] = []
        
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_text: str = None,
        from_email: str = None
    ) -> Dict[str, Any]:
        """
        Envoie un email via SendGrid ou SMTP
        
        Args:
            to_email: Email destinataire
            subject: Sujet de l'email
            html_body: Corps HTML
            plain_text: Corps texte (fallback)
            from_email: Email émetteur
            
        Returns:
            Dict avec status, message_id, timestamp
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # Essayer SendGrid en priorité
            if self.sendgrid_api_key:
                return self._send_sendgrid(
                    to_email, subject, html_body, plain_text, from_email, timestamp
                )
            
            # Fallback SMTP (Gmail)
            elif self.gmail_email and self.gmail_password:
                return self._send_smtp(
                    to_email, subject, html_body, plain_text, timestamp
                )
            
            else:
                error_msg = "❌ Aucun service email configuré (SendGrid ou Gmail)"
                self.logs.append(f"[{timestamp}] {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": timestamp,
                    "logs": self.logs
                }
                
        except Exception as e:
            error_msg = f"❌ Erreur envoi email: {str(e)}"
            self.logs.append(f"[{timestamp}] {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "timestamp": timestamp,
                "logs": self.logs
            }
    
    def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_text: str,
        from_email: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """Envoie via SendGrid API"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            
            mail = Mail(
                from_email=Email(from_email or "no-reply@imt.sn", "IMT Assistant"),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", plain_text or subject),
                html_content=Content("text/html", html_body)
            )
            
            response = sg.send(mail)
            message_id = response.headers.get("X-Message-ID")
            
            self.logs.append(f"[{timestamp}] ✅ Email SendGrid envoyé à {to_email}")
            
            return {
                "status": "success",
                "message": f"Email envoyé avec succès à {to_email}",
                "message_id": message_id,
                "to_email": to_email,
                "subject": subject,
                "timestamp": timestamp,
                "logs": self.logs
            }
            
        except Exception as e:
            self.logs.append(f"[{timestamp}] ❌ SendGrid error: {str(e)}")
            raise
    
    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_text: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """Envoie via SMTP (Gmail)"""
        try:
            # Créer le message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.gmail_email
            message["To"] = to_email
            
            # Ajouter les versions texte et HTML
            if plain_text:
                message.attach(MIMEText(plain_text, "plain"))
            message.attach(MIMEText(html_body, "html"))
            
            # Envoyer via SMTP Gmail
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.gmail_email, self.gmail_password)
                result = server.send_message(message)
            
            self.logs.append(f"[{timestamp}] ✅ Email SMTP envoyé à {to_email}")
            
            return {
                "status": "success",
                "message": f"Email envoyé avec succès à {to_email}",
                "message_id": f"smtp_{timestamp}",
                "to_email": to_email,
                "subject": subject,
                "timestamp": timestamp,
                "logs": self.logs
            }
            
        except Exception as e:
            self.logs.append(f"[{timestamp}] ❌ SMTP error: {str(e)}")
            raise


def send_director_email(
    user_request: str,
    user_name: str = "Utilisateur",
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour générer et envoyer un email au directeur
    
    Args:
        user_request: Demande de l'utilisateur
        user_name: Nom de l'utilisateur
        context: Contexte additionnel
        
    Returns:
        Dict avec status et résultats
    """
    timestamp = datetime.now().isoformat()
    
    try:
        # Générer l'email
        generator = DirectorEmailGenerator()
        email_data = generator.generate_formal_email(user_request, user_name, context)
        
        # Envoyer l'email
        sender = EmailSender()
        result = sender.send_email(
            to_email=email_data["to_email"],
            subject=email_data["subject"],
            html_body=email_data["body"],
            plain_text=email_data["plain_text"],
            from_email=email_data["from_email"]
        )
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Erreur envoi email: {str(e)}",
            "timestamp": timestamp
        }
