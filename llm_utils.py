import os
from typing import List, Tuple, Optional

def get_litellm_config() -> Tuple[Optional[str], List[str]]:
    """
    Retourne (modèle_primaire, liste_fallbacks) pour litellm.completion()
    Priorité: Groq > Gemini > Grok
    """
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

    # Nettoyage
    groq_key = (groq_key or "").strip().lstrip('=')
    gemini_key = (gemini_key or "").strip().lstrip('=')
    xai_key = (xai_key or "").strip().lstrip('=')

    if groq_key:
        primary = f"groq/{os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').replace('groq/', '')}"
        fallbacks = []
        if gemini_key: fallbacks.append(f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-flash-latest').replace('gemini/', '')}")
        if xai_key: fallbacks.append(f"xai/{os.getenv('GROK_MODEL', 'grok-2-latest').replace('xai/', '')}")
        return primary, fallbacks

    if gemini_key:
        primary = f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-flash-latest').replace('gemini/', '')}"
        fallbacks = ["gemini/gemini-2.0-flash"]
        if groq_key: fallbacks.insert(0, f"groq/{os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').replace('groq/', '')}")
        if xai_key: fallbacks.append(f"xai/{os.getenv('GROK_MODEL', 'grok-2-latest').replace('xai/', '')}")
        return primary, fallbacks

    if xai_key:
        primary = f"xai/{os.getenv('GROK_MODEL', 'grok-2-latest').replace('xai/', '')}"
        fallbacks = []
        if gemini_key: fallbacks.append(f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-flash-latest').replace('gemini/', '')}")
        return primary, fallbacks

    return None, []

def sanitize_env_keys():
    """Nettoie les clés API dans l'environnement pour éviter les erreurs de format"""
    for key in ["GROQ_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "GROK_API_KEY"]:
        val = os.getenv(key)
        if val:
            os.environ[key] = val.strip().lstrip('=')
