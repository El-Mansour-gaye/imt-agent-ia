import redis
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# =========================
# CONNEXION REDIS
# =========================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=1 # Evite d'attendre trop longtemps si Redis est mort
)

# Fallback en mémoire vive (RAM) si Redis est indisponible
_memory_fallback = {}

# =========================
# STOCKAGE DES MESSAGES
# =========================

def save_message(session_id: str, role: str, content: str):
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    key = f"session:{session_id}"
    try:
        redis_client.rpush(key, json.dumps(message))
    except Exception:
        if key not in _memory_fallback:
            _memory_fallback[key] = []
        _memory_fallback[key].append(json.dumps(message))


def get_last_messages(session_id: str, limit: int = 10) -> List[Dict]:
    key = f"session:{session_id}"
    try:
        raw = redis_client.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        raw = _memory_fallback.get(key, [])[-limit:]
        return [json.loads(m) for m in raw]


def get_all_messages(session_id: str) -> List[Dict]:
    key = f"session:{session_id}"
    try:
        raw = redis_client.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        raw = _memory_fallback.get(key, [])
        return [json.loads(m) for m in raw]


def count_messages(session_id: str) -> int:
    key = f"session:{session_id}"
    try:
        return redis_client.llen(key)
    except Exception:
        return len(_memory_fallback.get(key, []))

# =========================
# RÉSUMÉ AUTOMATIQUE
# =========================

def save_summary(session_id: str, summary: str):
    key = f"summary:{session_id}"
    try:
        redis_client.set(key, summary)
    except Exception:
        _memory_fallback[key] = summary


def get_summary(session_id: str) -> Optional[str]:
    key = f"summary:{session_id}"
    try:
        return redis_client.get(key)
    except Exception:
        return _memory_fallback.get(key)

# =========================
# CONTEXTE POUR AGENT IA
# =========================

def build_context(session_id: str, limit: int = 10) -> str:
    summary = get_summary(session_id)
    messages = get_last_messages(session_id, limit)
    context = ""
    if summary:
        context += f"Résumé de la conversation précédente:\n{summary}\n\n"
    context += "Derniers échanges:\n"
    for msg in messages:
        context += f"{msg['role'].upper()}: {msg['content']}\n"
    return context