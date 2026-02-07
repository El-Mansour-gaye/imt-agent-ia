"""
M2 Bonus - Sécurité et rate-limiting
Validation des intentions utilisateur et prévention du spam
"""
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

from dotenv import load_dotenv

load_dotenv()

@dataclass
class SecurityConfig:
    """Configuration de sécurité"""
    max_attempts_per_hour: int = 5
    max_forms_per_day: int = 3
    block_duration_hours: int = 1
    safety_threshold: float = 0.7
    captcha_trigger: int = 3  # Nombre d'échecs avant CAPTCHA

class RedisSecurityManager:
    """Gestionnaire de sécurité avec Redis"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.config = SecurityConfig()
        
        # Cache local si Redis non disponible
        self.local_cache = {}
        self.use_redis = redis_client is not None
        
        print(f"🔒 Gestionnaire de sécurité initialisé (Redis: {self.use_redis})")
    
    def _get_key(self, session_id: str, key_type: str) -> str:
        """Génère une clé Redis"""
        return f"security:{key_type}:{session_id}"
    
    def check_rate_limit(self, session_id: str, action_type: str = "query") -> Tuple[bool, str]:
        """
        Vérifie les limites de taux pour une session
        
        Returns:
            (allowed, message)
        """
        if not self.use_redis:
            # Vérification locale simple
            cache_key = f"{session_id}_{action_type}"
            
            if cache_key not in self.local_cache:
                self.local_cache[cache_key] = {
                    'count': 0,
                    'first_request': time.time(),
                    'last_request': time.time()
                }
            
            data = self.local_cache[cache_key]
            current_time = time.time()
            
            # Réinitialiser après 1 heure
            if current_time - data['first_request'] > 3600:
                data['count'] = 0
                data['first_request'] = current_time
            
            data['count'] += 1
            data['last_request'] = current_time
            
            if data['count'] > self.config.max_attempts_per_hour:
                return False, f"Limite dépassée ({data['count']}/{self.config.max_attempts_per_hour} requêtes/heure)"
            
            return True, f"OK ({data['count']}/{self.config.max_attempts_per_hour})"
        
        # Avec Redis
        key = self._get_key(session_id, f"rate_{action_type}")
        
        try:
            # Incrémenter le compteur
            current_count = self.redis.incr(key)
            
            # Si c'est la première requête, définir l'expiration
            if current_count == 1:
                self.redis.expire(key, 3600)  # Expire après 1 heure
            
            # Vérifier la limite
            if current_count > self.config.max_attempts_per_hour:
                block_key = self._get_key(session_id, "blocked")
                self.redis.setex(block_key, self.config.block_duration_hours * 3600, "blocked")
                
                return False, f"Trop de requêtes ({current_count}/{self.config.max_attempts_per_hour}). Blocage de {self.config.block_duration_hours}h."
            
            return True, f"OK ({current_count}/{self.config.max_attempts_per_hour})"
            
        except Exception as e:
            print(f"⚠️ Erreur Redis rate limit: {e}")
            return True, "Redis indisponible, sécurité réduite"
    
    def is_blocked(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Vérifie si une session est bloquée"""
        if not self.use_redis:
            # Vérification locale
            block_key = f"blocked_{session_id}"
            if block_key in self.local_cache:
                block_time = self.local_cache[block_key]
                if time.time() - block_time < self.config.block_duration_hours * 3600:
                    return True, f"Session bloquée jusqu'à {datetime.fromtimestamp(block_time + self.config.block_duration_hours * 3600)}"
                else:
                    del self.local_cache[block_key]
            return False, None
        
        # Avec Redis
        try:
            block_key = self._get_key(session_id, "blocked")
            ttl = self.redis.ttl(block_key)
            
            if ttl > 0:
                unblock_time = datetime.now() + timedelta(seconds=ttl)
                return True, f"Session bloquée jusqu'à {unblock_time.strftime('%H:%M:%S')}"
            
            return False, None
            
        except Exception as e:
            print(f"⚠️ Erreur Redis block check: {e}")
            return False, None
    
    def track_form_submission(self, session_id: str) -> Tuple[bool, str]:
        """Suit les soumissions de formulaire"""
        if not self.use_redis:
            # Tracking local
            form_key = f"forms_{session_id}"
            
            if form_key not in self.local_cache:
                self.local_cache[form_key] = {
                    'count': 0,
                    'date': datetime.now().date().isoformat()
                }
            
            data = self.local_cache[form_key]
            
            # Réinitialiser si nouvelle journée
            if data['date'] != datetime.now().date().isoformat():
                data['count'] = 0
                data['date'] = datetime.now().date().isoformat()
            
            data['count'] += 1
            
            if data['count'] > self.config.max_forms_per_day:
                return False, f"Limite formulaire atteinte ({data['count']}/{self.config.max_forms_per_day} par jour)"
            
            return True, f"Formulaire {data['count']}/{self.config.max_forms_per_day} aujourd'hui"
        
        # Avec Redis
        try:
            key = self._get_key(session_id, "forms_today")
            
            # Incrémenter avec expiration à minuit
            current_count = self.redis.incr(key)
            
            # Calculer les secondes jusqu'à minuit
            now = datetime.now()
            midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
            seconds_to_midnight = (midnight - now).seconds
            
            # Définir l'expiration si première soumission
            if current_count == 1:
                self.redis.expire(key, seconds_to_midnight)
            
            if current_count > self.config.max_forms_per_day:
                return False, f"Limite formulaire atteinte ({current_count}/{self.config.max_forms_per_day} par jour)"
            
            return True, f"Formulaire {current_count}/{self.config.max_forms_per_day} aujourd'hui"
            
        except Exception as e:
            print(f"⚠️ Erreur Redis form tracking: {e}")
            return True, "Redis indisponible, tracking réduit"
    
    def validate_with_gemini(self, query: str) -> Tuple[bool, float, str]:
        """
        Valide l'intention utilisateur avec Gemini Safety
        
        Args:
            query: Requête utilisateur
            
        Returns:
            (is_safe, confidence_score, message)
        """
        try:
            import google.generativeai as genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return True, 1.0, "GEMINI_API_KEY manquante, validation ignorée"
            
            genai.configure(api_key=api_key)
            # Utilisation du modèle flash-latest plus stable
            model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
            model = genai.GenerativeModel(model_name)
            
            prompt = f"""
            Analyse cette requête pour l'assistant IMT et évalue sa sécurité/intention.
            
            Requête: "{query}"
            
            Rends un verdict JSON avec:
            1. is_safe: true/false (la requête est-elle appropriée pour un assistant éducatif ?)
            2. confidence: 0.0 à 1.0 (confiance dans l'évaluation)
            3. reason: explication courte
            4. category: "information", "contact", "spam", "inappropriate", "other"
            
            Considérations:
            - L'assistant IMT aide avec les formations, frais, inscriptions
            - Refuse les demandes inappropriées, malveillantes ou hors contexte
            - Les demandes de contact (formulaire, email) sont autorisées
            - Le spam (repetitions, messages sans sens) doit être détecté
            
            Réponse JSON seulement:
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extraire le JSON de la réponse
            try:
                # Chercher des structures JSON dans la réponse
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    
                    is_safe = result.get('is_safe', True)
                    confidence = result.get('confidence', 0.5)
                    reason = result.get('reason', '')
                    category = result.get('category', 'other')
                    
                    return is_safe, confidence, f"{reason} (catégorie: {category})"
                else:
                    # Fallback si pas de JSON détecté
                    if any(word in response_text.lower() for word in ['unsafe', 'danger', 'refuse', 'inappropriate']):
                        return False, 0.6, "Requête potentiellement inappropriée détectée"
                    else:
                        return True, 0.8, "Requête apparemment sécuritaire"
                        
            except json.JSONDecodeError:
                # Analyse simple basée sur les mots-clés
                safe_keywords = ['frais', 'formation', 'inscription', 'contact', 'imt', 'dakar']
                unsafe_keywords = ['hack', 'attack', 'spam', '$$$', 'http://', 'https://']
                
                query_lower = query.lower()
                
                if any(unsafe in query_lower for unsafe in unsafe_keywords):
                    return False, 0.7, "Mot-clé suspect détecté"
                elif any(safe in query_lower for safe in safe_keywords):
                    return True, 0.9, "Requête éducative détectée"
                else:
                    return True, 0.5, "Requête neutre"
                    
        except Exception as e:
            print(f"⚠️ Erreur validation Gemini: {e}")
            # En cas d'erreur technique (quota, etc.), on effectue une validation par mots-clés
            # pour ne pas bloquer l'utilisateur inutilement.
            safe_keywords = ['frais', 'formation', 'inscription', 'contact', 'imt', 'dakar', 'salut', 'bonjour', 'aide']
            query_lower = query.lower()
            if any(safe in query_lower for safe in safe_keywords):
                return True, 0.9, "Validation par mots-clés (Fallback technique)"
            return True, 0.5, f"Erreur validation (neutre): {str(e)[:50]}"
    
    def simulate_captcha(self, session_id: str) -> Dict[str, Any]:
        """
        Simule un CAPTCHA audio pour accessibilité
        
        Returns:
            Dict avec défi CAPTCHA
        """
        # Générer un simple défi mathématique
        import random
        
        operations = [
            {"question": "Combien font 3 + 4 ?", "answer": "7"},
            {"question": "Quel est le résultat de 10 - 5 ?", "answer": "5"},
            {"question": "2 multiplié par 6 ?", "answer": "12"},
            {"question": "Première lettre de 'IMT' ?", "answer": "I"},
            {"question": "Capitale du Sénégal ?", "answer": "Dakar"}
        ]
        
        challenge = random.choice(operations)
        
        # Pour l'audio, on simule avec une description
        audio_description = f"""
        🔈 CAPTCHA Audio (simulation):
        Question: {challenge['question']}
        
        Pour les utilisateurs malvoyants, cette question serait lue à haute voix.
        Répondez avec le mot ou chiffre attendu.
        """
        
        return {
            "type": "audio_captcha_simulation",
            "question": challenge['question'],
            "audio_prompt": audio_description,
            "expected_answer": challenge['answer'],
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "note": "CAPTCHA simulé - En production, utiliser un service comme reCAPTCHA Audio"
        }
    
    def validate_user_intent(self, session_id: str, query: str) -> Dict[str, Any]:
        """
        Fonction principale de validation
        
        Args:
            session_id: ID de session utilisateur
            query: Requête utilisateur
            
        Returns:
            Dict avec résultats de validation
        """
        print(f"🔍 Validation sécurité pour session: {session_id}")
        
        results = {
            "session_id": session_id,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 1. Vérifier si la session est bloquée
        is_blocked, block_reason = self.is_blocked(session_id)
        results["checks"]["blocked"] = {
            "is_blocked": is_blocked,
            "reason": block_reason
        }
        
        if is_blocked:
            results["overall_allowed"] = False
            results["reason"] = f"Session bloquée: {block_reason}"
            return results
        
        # 2. Vérifier le rate limiting
        allowed_rate, rate_msg = self.check_rate_limit(session_id, "query")
        results["checks"]["rate_limit"] = {
            "allowed": allowed_rate,
            "message": rate_msg
        }
        
        if not allowed_rate:
            results["overall_allowed"] = False
            results["reason"] = f"Rate limit: {rate_msg}"
            return results
        
        # 3. Valider avec Gemini Safety
        is_safe, confidence, safety_msg = self.validate_with_gemini(query)
        results["checks"]["safety"] = {
            "is_safe": is_safe,
            "confidence": confidence,
            "message": safety_msg,
            "threshold": self.config.safety_threshold
        }
        
        if not is_safe or confidence < self.config.safety_threshold:
            # Vérifier si on doit déclencher un CAPTCHA
            fail_count = results["checks"].get("fail_count", 0) + 1
            results["checks"]["fail_count"] = fail_count
            
            if fail_count >= self.config.captcha_trigger:
                captcha = self.simulate_captcha(session_id)
                results["checks"]["captcha_required"] = captcha
                results["overall_allowed"] = False
                results["reason"] = f"CAPTCHA requis après {fail_count} échecs"
            else:
                results["overall_allowed"] = False
                results["reason"] = f"Validation sécurité échouée: {safety_msg}"
            
            return results
        
        # 4. Vérifier si c'est une demande de formulaire
        if any(keyword in query.lower() for keyword in ['formulaire', 'contact', 'remplir', 'envoyer']):
            form_allowed, form_msg = self.track_form_submission(session_id)
            results["checks"]["form_limit"] = {
                "allowed": form_allowed,
                "message": form_msg
            }
            
            if not form_allowed:
                results["overall_allowed"] = False
                results["reason"] = f"Limite formulaire: {form_msg}"
                return results
        
        # Toutes les vérifications passées
        results["overall_allowed"] = True
        results["reason"] = "Toutes les vérifications de sécurité passées"
        
        return results

# ==================== FONCTION D'EXPORT ====================
def validate_user_intent(query: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Fonction principale pour M3 - Validation sécurité
    
    Args:
        query: Requête utilisateur
        session_id: ID de session (optionnel)
        
    Returns:
        Résultats de validation
    """
    # Essayer de se connecter à Redis
    redis_client = None
    try:
        import redis
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True
        )
        redis_client.ping()
        print("✅ Redis connecté pour la sécurité")
    except:
        print("⚠️ Redis non disponible, sécurité locale seulement")
    
    manager = RedisSecurityManager(redis_client)
    result = manager.validate_user_intent(session_id, query)
    
    # Ajouter la clé 'allowed' pour compatibilité M3
    result['allowed'] = result.get('overall_allowed', True)
    
    return result

# ==================== TESTS ====================
def test_security():
    """Test du système de sécurité"""
    print("🔒 Test sécurité M2")
    print("=" * 60)
    
    # Créer un gestionnaire sans Redis (local seulement)
    manager = RedisSecurityManager()
    
    test_cases = [
        {
            "session": "test_user_1",
            "query": "Quels sont les frais de l'IMT ?",
            "description": "Requête légitime"
        },
        {
            "session": "test_user_2", 
            "query": "http://malicious.com hack system",
            "description": "Requête malveillante"
        },
        {
            "session": "test_spammer",
            "query": "spam spam spam",
            "description": "Spam détecté"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test['description']}")
        print(f"   Session: {test['session']}")
        print(f"   Requête: {test['query']}")
        
        result = manager.validate_user_intent(test['session'], test['query'])
        
        print(f"   Résultat: {'✅ AUTORISÉ' if result['overall_allowed'] else '❌ BLOQUÉ'}")
        print(f"   Raison: {result.get('reason', 'N/A')}")
        
        if not result['overall_allowed'] and 'captcha_required' in result['checks']:
            print(f"   CAPTCHA déclenché: {result['checks']['captcha_required']['question']}")
    
    # Test rate limiting
    print("\n📊 Test rate limiting:")
    for i in range(6):
        allowed, msg = manager.check_rate_limit("test_limit", "query")
        print(f"   Requête {i+1}: {msg}")
    
    print("\n" + "=" * 60)
    print("✅ Système de sécurité fonctionnel")

if __name__ == "__main__":
    test_security()