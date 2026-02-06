from redis import Redis
import csv
import io
import json

r = Redis(decode_responses=True, socket_connect_timeout=1)

# Fallback mémoire
_memory_fallback = {"queries": {}, "feedback": []}

def increment_query(type_: str):
    try:
        r.incr(f"analytics:query:{type_}")
    except Exception:
        _memory_fallback["queries"][type_] = _memory_fallback["queries"].get(type_, 0) + 1

def save_feedback(session_id: str, score: int):
    data = {"session": session_id, "score": score}
    try:
        r.rpush("analytics:feedback", json.dumps(data))
    except Exception:
        _memory_fallback["feedback"].append(data)

def get_query_counts():
    """Retourne les compteurs par type de requête (analytics:query:*)."""
    try:
        keys = r.keys("analytics:query:*")
        return {k.replace("analytics:query:", ""): int(r.get(k) or 0) for k in keys}
    except Exception:
        return _memory_fallback["queries"].copy()

def get_feedback_list():
    """Retourne la liste des feedbacks (session, score) depuis Redis."""
    try:
        raw = r.lrange("analytics:feedback", 0, -1) or []
        return [json.loads(x) for x in raw]
    except Exception:
        return _memory_fallback["feedback"].copy()

def export_analytics_csv() -> str:
    """
    Exporte les analytics (compteurs requêtes + feedbacks) en CSV.
    Retourne le chemin du fichier créé.
    """
    out = io.StringIO()
    writer = csv.writer(out)

    # Section compteurs requêtes
    writer.writerow(["type", "count"])
    for qtype, count in sorted(get_query_counts().items()):
        writer.writerow([qtype, count])

    writer.writerow([])
    writer.writerow(["session", "score"])
    for fb in get_feedback_list():
        writer.writerow([fb.get("session", ""), fb.get("score", "")])

    path = "analytics_export.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out.getvalue())
    return path
