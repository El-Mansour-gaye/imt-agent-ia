# BRANCH: feature/m1-auto-refresh
import os
import time
import json
import redis
import google.generativeai as genai
from datetime import datetime, timedelta
from dotenv import load_dotenv
from scrape_imt import run_spider
from rag_tools import index_documents, imt_rag_search

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_KEY = "imt:last_scrape_timestamp"

def get_redis_client():
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return None

def refresh_data_if_stale(days=7):
    r = get_redis_client()
    stale = False
    last_scrape = None

    if r:
        last_scrape = r.get(REDIS_KEY)
        if last_scrape:
            last_scrape_dt = datetime.fromtimestamp(float(last_scrape))
            if datetime.now() - last_scrape_dt > timedelta(days=days):
                stale = True
            else:
                days_ago = (datetime.now() - last_scrape_dt).days
                print(f"Données à jour ({days_ago} jours)")
        else:
            stale = True
    else:
        # Fallback if Redis is down: consider data stale
        print("Redis down, considering data stale...")
        stale = True

    if stale:
        print("Starting re-scrape...")
        run_spider()

        print("Re-indexing documents...")
        chunks_count = index_documents("imt_data.json", rebuild=True)

        # Count pages for log
        with open("imt_data.json", "r") as f:
            data = json.load(f)
            pages_count = len(data)

        print(f"Rafraîchi {pages_count} pages, {chunks_count} chunks")

        if r:
            r.set(REDIS_KEY, time.time())

    return stale

def imt_enhanced_search(query: str):
    # 1. Get chunks from RAG
    chunks = imt_rag_search(query)

    if not chunks:
        return {"answer": "Désolé, je n'ai pas trouvé d'informations à ce sujet.", "sources": []}

    # 2. Build context for Gemini
    context = "\n\n".join([f"Source: {c['source']}\nContent: {c['content']}" for c in chunks])

    prompt = f"""
Tu es un assistant expert pour l'IMT (Institut de Management et de Technologie).
Utilise les extraits suivants pour répondre à la question de l'utilisateur.
Si tu ne connais pas la réponse, dis que tu ne sais pas.
Ta réponse doit être précise et concise.

Extraits :
{context}

Question : {query}
"""

    try:
        import litellm
        from llm_utils import get_litellm_config, sanitize_env_keys

        sanitize_env_keys()
        primary, fallbacks = get_litellm_config()

        response = litellm.completion(
            model=primary,
            messages=[{"role": "user", "content": prompt}],
            fallbacks=fallbacks,
            temperature=0.4
        )
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Search LLM failed: {e}")
        # Very basic fallback
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        answer = response.text

    # 3. Format result
    sources = [{"url": c['source'], "snippet": c['content'][:200] + "..."} for c in chunks]

    return {
        "answer": answer,
        "sources": sources
    }
