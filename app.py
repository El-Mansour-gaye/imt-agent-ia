# =========================
# IMPORTS
# =========================
import chainlit as cl
import base64
import uuid
import numpy as np
import soundfile as sf
import sys
import os
import asyncio
import tempfile
import litellm

# Ajouter le dossier actuel au path pour éviter les erreurs d'import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langfuse import get_client as get_langfuse_client, observe

from redis_manager import (
    save_message,
    get_last_messages,
    get_all_messages,
    count_messages,
    save_summary,
    get_summary,
    build_context,
    get_all_session_ids
)
from analytics import (
    increment_query,
    save_feedback,
    export_analytics_csv,
    get_query_counts,
    get_feedback_list
)
from pdf_generator import generate_reco_pdf
from voice import stt_from_audio, tts_to_audio
from rag_tools import get_collection_stats
from datetime import datetime

# Intégration M2 - CrewAI & Actions
from m2_crewai.crewai_config import get_imt_crew
from llm_utils import get_litellm_config, sanitize_env_keys

# =========================
# INITIALISATION
# =========================
sanitize_env_keys()

# =========================
# UTILITAIRES
# =========================
def create_session_id():
    return f"IMT-{uuid.uuid4().hex[:8]}"

def get_data_age():
    try:
        mtime = os.path.getmtime("imt_data.json")
        days = (datetime.now().timestamp() - mtime) // (24 * 3600)
        return int(days)
    except Exception:
        return 0

async def show_admin_dashboard():
    chunks = get_collection_stats()
    days = get_data_age()
    counts = get_query_counts()

    top_formation = "N/A"
    if counts:
        top_formation = max(counts, key=counts.get)

    cost = 0.02
    latency = 1.2

    feedbacks = get_feedback_list()
    if feedbacks:
        positive = sum(1 for f in feedbacks if f.get("score", 0) > 0)
        percent = (positive / len(feedbacks)) * 100
        fb_text = f"👍 {percent:.0f}% ({positive}/{len(feedbacks)})"
    else:
        fb_text = "👍 100% (0/0)"

    metrics_content = f"""
### 🛠️ ESPACE ADMIN - Dashboard Live
**Session ID actuelle:** `{cl.user_session.get("session_id")}`
**Statut Serveur:** 🟢 Opérationnel

---
**📦 RAG & DATA:**
- 🧩 Chunks indexés: `{chunks}`
- 📅 Fraîcheur: `{days} jours`
- 🌍 Langues: `FR / Wolof (TTS)`

---
**⚡ PERFORMANCE & COÛT:**
- 💸 Coût estimé: `{cost}$`
- ⏱️ Latence moy: `{latency}s`
- {fb_text}

---
**📈 ANALYTICS:**
- Top Formation: `{top_formation.upper()}`
- Total Sessions: `{len(get_all_session_ids())}`
"""

    session_ids = get_all_session_ids()
    session_actions = [
        cl.Action(name="view_history", value=sid, label=f"📜 {sid[:8]}", payload={"sid": sid})
        for sid in session_ids[-5:] # Montrer les 5 dernières
    ]

    await cl.Message(
        content=f"### 🔐 Accès Admin Autorisé\n\n{metrics_content}",
        actions=session_actions + [cl.Action(name="refresh_admin", value="refresh", label="🔄 Actualiser", payload={})]
    ).send()

async def call_agent(user_message: str, session_id: str) -> str:
    """Appel réel à l'agent CrewAI (M2)"""
    try:
        crew = get_imt_crew(session_id)
        # On passe la query à CrewAI (kickoff est synchrone)
        result = await cl.make_async(crew.kickoff)({"query": user_message})
        
        if result.get("success"):
            return result["response"]
        else:
            return f"⚠️ Une erreur est survenue dans l'agent : {result.get('error')}"
    except Exception as e:
        return f"❌ Erreur critique lors de l'appel à l'agent : {str(e)}"

# =========================
# LANGFUSE – TRACE PRINCIPALE
# =========================
@observe(name="trace_agent_query")
async def handle_agent(session_id: str, user_message: str) -> str:
    increment_query("general")
    return await call_agent(user_message=user_message, session_id=session_id)

# =========================
# CHAINLIT START
# =========================
@cl.on_chat_start
async def on_chat_start():
    session_id = create_session_id()
    cl.user_session.set("session_id", session_id)

    actions = [
        cl.Action(name="fill_form", value="form", label="📝 Remplir Formulaire", payload={}),
        cl.Action(name="send_email", value="email", label="📧 Email Directeur", payload={}),
        cl.Action(name="gen_pdf", value="pdf", label="📥 PDF Recommandations", payload={}),
        cl.Action(name="admin_mode", value="admin", label="🛠️ Admin", payload={}),
    ]

    await cl.Message(
        content=f"""
👋 **Bienvenue sur l’assistant IA de l’IMT**

🆔 Session : `{session_id}`  
💾 Mémoire : **Activée** (Persistance JSON)

Posez vos questions sur les formations, les frais ou l'admission.
""",
        actions=actions
    ).send()

# =========================
# MESSAGES TEXTE
# =========================
@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")

    actions = [
        cl.Action(name="fill_form", value="form", label="📝 Remplir Formulaire", payload={}),
        cl.Action(name="send_email", value="email", label="📧 Email Directeur", payload={}),
        cl.Action(name="gen_pdf", value="pdf", label="📥 PDF Recommandations", payload={}),
    ]

    # Message d'attente
    msg = cl.Message(content="🤖 Analyse en cours...")
    await msg.send()

    response = await handle_agent(session_id, message.content)

    # Simulation de streaming pour l'UX
    final_msg = cl.Message(content="", actions=actions)
    for token in response.split(" "):
        await final_msg.stream_token(token + " ")
        await asyncio.sleep(0.02) # Petit délai pour l'effet visuel

    await final_msg.send()
    # On supprime le message d'attente
    await msg.remove()

# =========================
# ACTIONS UI
# =========================
@cl.action_callback("gen_pdf")
async def gen_pdf_callback(action):
    session_id = cl.user_session.get("session_id")
    await cl.Message(content="📥 **Génération de votre PDF personnalisé en cours...**").send()

    # On récupère l'historique pour l'IA
    history = build_context(session_id)

    # Appel simplifié à l'IA pour générer le contenu du PDF
    # (On utilisera Gemini via litellm comme convenu)
    primary, fallbacks = get_litellm_config()
    prompt = f"Basé sur cet historique, génère une recommandation d'étude personnalisée pour l'étudiant à l'IMT (Profil, Recommandation, Dates, Actions):\n\n{history}"

    try:
        res = await cl.make_async(litellm.completion)(
            model=primary,
            messages=[{"role": "user", "content": prompt}],
            fallbacks=fallbacks
        )
        profile_text = res.choices[0].message.content

        pdf_path = generate_reco_pdf(profile_text)

        await cl.Message(
            content=f"✅ Votre recommandation est prête !",
            elements=[cl.File(name="reco_mansour_isi.pdf", path=pdf_path, display="inline")]
        ).send()
    except Exception as e:
        await cl.Message(content=f"❌ Erreur PDF : {str(e)}").send()

@cl.action_callback("admin_mode")
async def admin_mode_callback(action):
    await show_admin_dashboard()

@cl.action_callback("refresh_admin")
async def refresh_admin_callback(action):
    await show_admin_dashboard()

@cl.action_callback("view_history")
async def view_history_callback(action):
    sid = action.payload.get("sid")
    messages = get_all_messages(sid)

    history_text = f"### 📜 Historique de la Session `{sid}`\n\n"
    if not messages:
        history_text += "Aucun message trouvé."
    else:
        for m in messages:
            role = "👤 USER" if m["role"] == "user" else "🤖 IA"
            history_text += f"**[{m['timestamp'][:16]}] {role}:** {m['content']}\n\n"

    await cl.Message(content=history_text).send()

@cl.action_callback("fill_form")
async def fill_form_callback(action):
    session_id = cl.user_session.get("session_id")
    query = "Je souhaite remplir le formulaire de contact."
    await cl.Message(content=f"📝 **Action demandée :** {query}").send()
    msg = cl.Message(content="🤖 Analyse en cours...")
    await msg.send()
    response = await handle_agent(session_id, query)

    final_msg = cl.Message(content="")
    for token in response.split(" "):
        await final_msg.stream_token(token + " ")
        await asyncio.sleep(0.01)
    await final_msg.send()
    await msg.remove()

@cl.action_callback("send_email")
async def send_email_callback(action):
    session_id = cl.user_session.get("session_id")
    query = "Je souhaite envoyer un email au directeur."
    await cl.Message(content=f"📧 **Action demandée :** {query}").send()
    msg = cl.Message(content="🤖 Analyse en cours...")
    await msg.send()
    response = await handle_agent(session_id, query)

    final_msg = cl.Message(content="")
    for token in response.split(" "):
        await final_msg.stream_token(token + " ")
        await asyncio.sleep(0.01)
    await final_msg.send()
    await msg.remove()

# =========================
# FEEDBACK
# =========================
@cl.on_feedback
async def on_feedback(feedback):
    session_id = cl.user_session.get("session_id")
    score = 1 if feedback.value == "positive" else -1
    save_feedback(session_id, score)
    await cl.Message(content="Merci pour votre retour ! 👍").send()

# =========================
# VOICE I/O
# =========================
@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    if chunk.is_first:
        cl.user_session.set("audio_buffer", b"")

    buffer = cl.user_session.get("audio_buffer")
    cl.user_session.set("audio_buffer", buffer + chunk.data)

@cl.on_audio_end
async def on_audio_end(elements: list):
    audio_chunk = cl.user_session.get("audio_buffer")
    if not audio_chunk:
        return

    # Sauvegarder temporairement l'audio pour STT
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
        tmp_audio.write(audio_chunk)
        tmp_path = tmp_audio.name

    try:
        # 1. STT
        text = await cl.make_async(stt_from_audio)(tmp_path)
        await cl.Message(content=f"🎤 **Vous avez dit :** {text}").send()

        # 2. Agent
        session_id = cl.user_session.get("session_id")
        response = await handle_agent(session_id, text)

        # 3. TTS
        audio_path = await cl.make_async(tts_to_audio)(response)

        # 4. Envoi
        await cl.Message(content=response).send()
        await cl.Audio(path=audio_path, name="Réponse Vocale", display="inline").send()

    except Exception as e:
        await cl.Message(content=f"⚠️ Erreur Voice : {str(e)}").send()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)