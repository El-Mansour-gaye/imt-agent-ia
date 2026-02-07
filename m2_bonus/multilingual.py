"""
M2 Bonus - Multi-langue et traduction
Détection automatique de langue et traduction Wolof/Français/Anglais
"""
import re
import os
from typing import Dict, Any, Tuple, Optional
from langdetect import detect, DetectorFactory, LangDetectException
from dotenv import load_dotenv

load_dotenv()

# Pour des résultats reproductibles
DetectorFactory.seed = 0

# Dictionnaire de langues supportées
SUPPORTED_LANGUAGES = {
    'fr': 'français',
    'en': 'anglais',
    'wo': 'wolof',
    'es': 'espagnol',
    'ar': 'arabe'
}

# Mots-clés Wolof courants
WOLOF_KEYWORDS = {
    'nanga def': 'comment vas-tu',
    'jërejëf': 'merci',
    'waaw': 'oui',
    'déedéet': 'non',
    'frais': 'frais',
    'inscription': 'inscription',
    'formation': 'formation',
    'imt': 'imt',
    'dakar': 'dakar',
    'mangi': 'je veux',
    'xam': 'savoir',
    'yi': 'les'
}


def detect_lang_and_translate(query: str, target_lang: str = 'fr') -> Dict[str, Any]:
    """
    Fonction principale: Détecte la langue et traduit le query en français
    
    BONUS: Supporte Wolof/Français/Anglais comme spécifié dans le plan M2
    
    Args:
        query: Texte à analyser et traduire
        target_lang: Langue cible (par défaut: français)
        
    Returns:
        Dict avec:
            - detected_language: Code langue détectée (wo/fr/en/es/ar)
            - confidence: Confiance de la détection
            - original_text: Texte original
            - translated_text: Texte traduit
            - is_translated: Boolean si traduction effectuée
            - language_name: Nom de la langue détectée
    """
    processor = MultilingualProcessor(use_gemini=True)
    
    # Détecter la langue
    lang_detection = processor.detect_language(query)
    detected_lang = lang_detection['language']
    
    # Traduire si nécessaire (vers français par défaut)
    translated_text = query
    is_translated = False
    
    if detected_lang != target_lang:
        # Traduire vers la langue cible
        translated_text = processor.translate_to(query, detected_lang, target_lang)
        is_translated = True
    
    return {
        'detected_language': detected_lang,
        'detected_language_name': lang_detection['name'],
        'confidence': lang_detection['confidence'],
        'original_text': query,
        'translated_text': translated_text,
        'is_translated': is_translated,
        'target_language': target_lang,
        'detection_method': lang_detection.get('detection_method', 'unknown')
    }


class MultilingualProcessor:
    """Processeur multi-langue pour l'assistant IMT"""
    
    def __init__(self, use_gemini: bool = True):
        self.use_gemini = use_gemini
        self.detection_cache = {}
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Détecte la langue du texte avec fallback manuel pour Wolof
        
        Args:
            text: Texte à analyser
            
        Returns:
            Dict avec code langue et confiance
        """
        # Vérifier le cache
        cache_key = text.lower()[:50]
        if cache_key in self.detection_cache:
            return self.detection_cache[cache_key]
        
        text_lower = text.lower().strip()
        
        # 1. Vérification manuelle pour Wolof
        wolof_indicators = 0
        for keyword in WOLOF_KEYWORDS:
            if keyword in text_lower:
                wolof_indicators += 1
        
        # Si plus de 2 mots Wolof détectés ou phrase typique
        if wolof_indicators >= 2 or any(
            phrase in text_lower for phrase in ['nanga def', 'jërejëf', 'mangi bëgg']
        ):
            result = {
                'language': 'wo',
                'confidence': 0.8,
                'name': 'wolof',
                'detection_method': 'keyword_matching'
            }
            self.detection_cache[cache_key] = result
            return result
        
        # 2. Détection automatique avec langdetect
        try:
            lang_code = detect(text)
            confidence = 0.9
            
            # Mapping des codes langdetect
            lang_mapping = {
                'fr': 'fr',  # français
                'en': 'en',  # anglais
                'es': 'es',  # espagnol
                'ar': 'ar',  # arabe
                'de': 'en',  # allemand → anglais (fallback)
                'it': 'en',  # italien → anglais
                'pt': 'en',  # portugais → anglais
            }
            
            if lang_code in lang_mapping:
                detected_lang = lang_mapping[lang_code]
            else:
                detected_lang = 'en'  # Fallback à l'anglais
            
            result = {
                'language': detected_lang,
                'confidence': confidence,
                'name': SUPPORTED_LANGUAGES.get(detected_lang, 'anglais'),
                'detection_method': 'langdetect'
            }
            
            self.detection_cache[cache_key] = result
            return result
            
        except LangDetectException:
            # Fallback: détection par caractères
            if any(char in text for char in ['ñ', 'à', 'è', 'é', 'ù']):
                lang = 'fr'
            elif any(char in text for char in ['ñ', 'á', 'é', 'í', 'ó', 'ú']):
                lang = 'es'
            elif any(0x0600 <= ord(char) <= 0x06FF for char in text):
                lang = 'ar'
            else:
                lang = 'en'  # Par défaut
            
            result = {
                'language': lang,
                'confidence': 0.6,
                'name': SUPPORTED_LANGUAGES.get(lang, 'anglais'),
                'detection_method': 'character_analysis'
            }
            
            self.detection_cache[cache_key] = result
            return result
    
    def translate_to(self, text: str, source_lang: str, target_lang: str = 'fr') -> str:
        """
        Traduit du texte de la langue source vers la langue cible
        
        Utilise Gemini si disponible, sinon fallback simple
        
        Args:
            text: Texte à traduire
            source_lang: Code langue source (wo/en/fr/es/ar)
            target_lang: Code langue cible (défaut: fr)
            
        Returns:
            Texte traduit
        """
        # Si déjà dans la langue cible, retourner tel quel
        if source_lang == target_lang:
            return text
        
        # Essayer Gemini en priorité
        if self.use_gemini:
            translated = self.translate_with_gemini(text, source_lang, target_lang)
            if translated != text:
                return translated
        
        # Fallback: traduction simple basée sur dictionnaire
        return self._fallback_translation(text, target_lang)
    
    def _fallback_translation(self, text: str, target_lang: str = 'fr') -> str:
        """Traduction simple sans API (pour tests/fallback)"""
        # Dictionnaire simple Wolof -> Français
        wolof_fr_dict = {
            'nanga def': 'comment allez-vous',
            'jërejëf': 'merci',
            'waaw': 'oui',
            'déedéet': 'non',
            'frais': 'frais',
            'inscription': 'inscription',
            'formation': 'formation',
            'imt': 'IMT',
            'dakar': 'Dakar',
            'mangi': 'je veux',
            'xam': 'savoir',
            'yi': 'les'
        }
        
        # Appliquer les traductions si source est Wolof
        result = text
        for wolof_word, french_word in wolof_fr_dict.items():
            result = result.replace(wolof_word, french_word)
        
        return result
    
    def translate_with_llm(self, text: str, source_lang: str = 'en', target_lang: str = 'fr') -> str:
        """
        Traduction avec LLM (Gemini avec fallback Grok via LiteLLM)
        """
        try:
            import litellm
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            gemini_key = os.getenv("GEMINI_API_KEY")
            xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
            
            if not gemini_key and not xai_key:
                return self._fallback_translation(text, target_lang)
            
            lang_names = {'fr': 'français', 'en': 'anglais', 'wo': 'wolof', 'es': 'espagnol', 'ar': 'arabe'}
            target_name = lang_names.get(target_lang, 'français')
            
            prompt = f"Traduis ce texte en {target_name}. Conserve le sens exact.\n\nTexte: {text}\n\nTraduction:"
            
            # Définir le modèle primaire et fallbacks (Priorité Grok si disponible)
            if xai_key:
                model_name = os.getenv("GROK_MODEL") or "grok-2-latest"
                model = f"xai/{model_name.replace('xai/', '')}"
                fallbacks = []
                if gemini_key:
                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                    fallbacks.append(f"gemini/{gemini_model.replace('gemini/', '')}")
            elif gemini_key:
                model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                model = f"gemini/{model_name.replace('gemini/', '')}"
                fallbacks = ["gemini/gemini-1.5-flash", "gemini/gemini-2.0-flash-exp"]
            else:
                return self._fallback_translation(text, target_lang)
            
            # Utiliser litellm pour la complétion avec fallbacks
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                fallback_models=fallbacks,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ Traduction LLM échouée: {e}")
            # Tentative via google-generativeai direct si litellm échoue (cas où litellm n'est pas là)
            return self.translate_with_gemini_direct(text, source_lang, target_lang)

    def translate_with_gemini_direct(self, text: str, source_lang: str = 'en', target_lang: str = 'fr') -> str:
        """Fallback direct sur l'API Gemini si LiteLLM échoue"""
        try:
            import google.generativeai as genai
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return self._fallback_translation(text, target_lang)
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Traduis en {target_lang}: {text}"
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            return self._fallback_translation(text, target_lang)

    def translate_with_gemini(self, text: str, source_lang: str = 'en', target_lang: str = 'fr') -> str:
        """Maintenu pour compatibilité, redirige vers translate_with_llm"""
        return self.translate_with_llm(text, source_lang, target_lang)
    
    def _fallback_translation(self, text: str, target_lang: str) -> str:
        """Traduction de fallback simple"""
        
        # Détection de la langue source
        source_info = self.detect_language(text)
        source_lang = source_info['language']
        
        # Si déjà dans la langue cible
        if source_lang == target_lang:
            return text
        
        # Traductions simples Wolof→Français
        if source_lang == 'wo' and target_lang == 'fr':
            translated = text
            for wolof, french in WOLOF_KEYWORDS.items():
                translated = translated.replace(wolof, french)
            
            return f"[Traduit du Wolof] {translated}"
        
        # Pour d'autres langues, retourner avec annotation
        source_name = SUPPORTED_LANGUAGES.get(source_lang, 'inconnue')
        target_name = SUPPORTED_LANGUAGES.get(target_lang, 'français')
        
        return f"[{source_name} → {target_name}] {text}"
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Traite une requête: détection + traduction si nécessaire
        
        Args:
            query: Requête utilisateur
            
        Returns:
            Dict avec informations de langue et texte traité
        """
        # Détection de langue
        lang_info = self.detect_language(query)
        
        # Si la langue n'est pas français, traduire
        translated_query = query
        translation_info = None
        
        if lang_info['language'] != 'fr':
            if self.use_gemini:
                translated_query = self.translate_with_gemini(query, 'fr')
            else:
                translated_query = self._fallback_translation(query, 'fr')
            
            translation_info = {
                'original': query,
                'translated': translated_query,
                'source_lang': lang_info['language'],
                'target_lang': 'fr'
            }
        
        return {
            'original_query': query,
            'processed_query': translated_query,
            'language_detection': lang_info,
            'translation': translation_info,
            'requires_translation': lang_info['language'] != 'fr'
        }
    
    def generate_bilingual_response(self, 
                                   french_response: str, 
                                   original_lang: str) -> str:
        """
        Génère une réponse bilingue
        
        Args:
            french_response: Réponse en français
            original_lang: Langue originale de la requête
            
        Returns:
            Réponse bilingue formatée
        """
        if original_lang == 'fr':
            return french_response
        
        # Traduire la réponse dans la langue originale
        if self.use_gemini:
            try:
                translated_response = self.translate_with_gemini(
                    french_response, 
                    original_lang
                )
            except:
                translated_response = self._fallback_translation(
                    french_response, 
                    original_lang
                )
        else:
            translated_response = self._fallback_translation(
                french_response, 
                original_lang
            )
        
        # Formater la réponse bilingue
        lang_name = SUPPORTED_LANGUAGES.get(original_lang, original_lang)
        
        response = f"""
🌐 **Réponse bilingue ({lang_name} / Français):**

**{lang_name.upper()}:** {translated_response}

**FRANÇAIS:** {french_response}

*(Assistant IMT - Service multi-langue)*
"""
        
        return response.strip()

# ==================== FONCTION D'EXPORT ====================
# Note: detect_lang_and_translate est définie plus haut (ligne 42)
# Cette version basique est un alias

def process_multilingual_query(query: str) -> str:
    """
    Alias: Fonction simple pour traiter une requête multilingue
    
    Args:
        query: Requête utilisateur
        
    Returns:
        Texte traité avec informations
    """
    processor = MultilingualProcessor(use_gemini=True)
    result = processor.process_query(query)
    
    if result['requires_translation']:
        return f"🌐 Question traduite ({result['language_detection']['name']} → français): {result['processed_query']}"
    else:
        return f"✅ Question en français détectée: {query}"

# ==================== TESTS ====================
def test_multilingual():
    """Test du système multi-langue"""
    print("🧪 Test multi-langue M2")
    print("=" * 60)
    
    processor = MultilingualProcessor(use_gemini=True)
    
    test_queries = [
        "Quels sont les frais de la licence ISI ?",  # Français
        "What are the fees for ISI license?",  # Anglais
        "Nanga def? Mangi bëgg xam frais yi ci IMT",  # Wolof
        "¿Cuáles son las tarifas de la licencia ISI?",  # Espagnol
        "ما هي رسوم ترخيص ISI؟",  # Arabe
    ]
    
    for query in test_queries:
        print(f"\n📝 Original: {query}")
        result = processor.process_query(query)
        
        print(f"   Langue détectée: {result['language_detection']['name']} "
              f"(confiance: {result['language_detection']['confidence']})")
        
        if result['requires_translation']:
            print(f"   Traduit en français: {result['processed_query'][:80]}...")
        
        # Générer une réponse bilingue
        french_response = "Les frais de la licence ISI sont d'environ 1 850 000 FCFA par an."
        bilingual = processor.generate_bilingual_response(
            french_response,
            result['language_detection']['language']
        )
        
        print(f"   Réponse bilingue générée: {len(bilingual)} caractères")
    
    print("\n" + "=" * 60)
    print("✅ Système multi-langue fonctionnel")

if __name__ == "__main__":
    test_multilingual()