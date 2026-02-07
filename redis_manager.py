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

# Fallback persistant (JSON) si Redis est indisponible
SESSION_FILE = "sessions.json"

def _load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_sessions(data):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving sessions: {e}")

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
        data = _load_sessions()
        if key not in data:
            data[key] = []
        data[key].append(json.dumps(message))
        _save_sessions(data)


def get_last_messages(session_id: str, limit: int = 10) -> List[Dict]:
    key = f"session:{session_id}"
    try:
        raw = redis_client.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        data = _load_sessions()
        raw = data.get(key, [])[-limit:]
        return [json.loads(m) for m in raw]


def get_all_messages(session_id: str) -> List[Dict]:
    key = f"session:{session_id}"
    try:
        raw = redis_client.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]
    except Exception:
        data = _load_sessions()
        raw = data.get(key, [])
        return [json.loads(m) for m in raw]


def count_messages(session_id: str) -> int:
    key = f"session:{session_id}"
    try:
        return redis_client.llen(key)
    except Exception:
        data = _load_sessions()
        return len(data.get(key, []))

# =========================
# RÉSUMÉ AUTOMATIQUE
# =========================

def save_summary(session_id: str, summary: str):
    key = f"summary:{session_id}"
    try:
        redis_client.set(key, summary)
    except Exception:
        data = _load_sessions()
        data[key] = summary
        _save_sessions(data)


def get_summary(session_id: str) -> Optional[str]:
    key = f"summary:{session_id}"
    try:
        return redis_client.get(key)
    except Exception:
        data = _load_sessions()
        return data.get(key)

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