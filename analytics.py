from redis import Redis
import csv
import io
import json

r = Redis(decode_responses=True)

def increment_query(type_: str):
    r.incr(f"analytics:query:{type_}")

def save_feedback(session_id: str, score: int):
    r.rpush("analytics:feedback", json.dumps({
        "session": session_id,
        "score": score
    }))

def get_query_counts():
    """Retourne les compteurs par type de requête (analytics:query:*)."""
    keys = r.keys("analytics:query:*")
    return {k.replace("analytics:query:", ""): int(r.get(k) or 0) for k in keys}

def get_feedback_list():
    """Retourne la liste des feedbacks (session, score) depuis Redis."""
    raw = r.lrange("analytics:feedback", 0, -1) or []
    return [json.loads(x) for x in raw]

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
