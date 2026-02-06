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
    decode_responses=True
)

# =========================
# STOCKAGE DES MESSAGES
# =========================

def save_message(session_id: str, role: str, content: str):
    key = f"session:{session_id}"
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    redis_client.rpush(key, json.dumps(message))


def get_last_messages(session_id: str, limit: int = 10) -> List[Dict]:
    key = f"session:{session_id}"
    raw = redis_client.lrange(key, -limit, -1)
    return [json.loads(m) for m in raw]


def get_all_messages(session_id: str) -> List[Dict]:
    key = f"session:{session_id}"
    raw = redis_client.lrange(key, 0, -1)
    return [json.loads(m) for m in raw]


def count_messages(session_id: str) -> int:
    return redis_client.llen(f"session:{session_id}")

# =========================
# RÉSUMÉ AUTOMATIQUE
# =========================

def save_summary(session_id: str, summary: str):
    redis_client.set(f"summary:{session_id}", summary)


def get_summary(session_id: str) -> Optional[str]:
    return redis_client.get(f"summary:{session_id}")

# =========================
# CONTEXTE POUR AGENT IA
# =========================

def build_context(session_id: str, limit: int = 10) -> str:
    """
    Construit le contexte à injecter dans CrewAI / LLM
    """
    summary = get_summary(session_id)
    messages = get_last_messages(session_id, limit)

    context = ""

    if summary:
        context += f"Résumé de la conversation précédente:\n{summary}\n\n"

    context += "Derniers échanges:\n"

    for msg in messages:
        context += f"{msg['role'].upper()}: {msg['content']}\n"

    return context
