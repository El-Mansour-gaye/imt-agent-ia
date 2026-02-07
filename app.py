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

# Ajouter le dossier actuel au path pour éviter les erreurs d'import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langfuse import get_client as get_langfuse_client, observe

from redis_manager import (
    save_message,
    get_last_messages,
    count_messages,
    save_summary,
    get_summary,
    build_context
)
from analytics import increment_query, save_feedback, export_analytics_csv
from pdf_generator import generate_reco_pdf
from voice import stt_from_audio, tts_to_audio

# Intégration M2 - CrewAI & Actions
from m2_crewai.crewai_config import get_imt_crew

# =========================
# UTILITAIRES
# =========================
def create_session_id():
    return f"IMT-{uuid.uuid4().hex[:8]}"

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

    await cl.Message(
        content=f"""
👋 **Bienvenue sur l’assistant IA de l’IMT**

🆔 Session : `{session_id}`  
💾 Mémoire : **Activée** (Auto-fallback si Redis absent)

Posez vos questions sur les formations, les frais ou l'admission.
""",
        actions=[
            cl.Action(name="fill_form", value="form", label="📝 Remplir le formulaire", payload={}),
            cl.Action(name="send_email", value="email", label="📧 Écrire au directeur", payload={}),
        ]
    ).send()

# =========================
# MESSAGES TEXTE
# =========================
@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    # Note: La sauvegarde des messages est gérée par l'agent CrewAI (M2)
    # pour éviter les doublons dans l'historique Redis.
    await cl.Message(content="🤖 Analyse en cours...").send()
    response = await handle_agent(session_id, message.content)
    await cl.Message(content=response).send()

# =========================
# ACTIONS UI
# =========================
@cl.action_callback("fill_form")
async def fill_form_callback(action):
    session_id = cl.user_session.get("session_id")
    query = "Je souhaite remplir le formulaire de contact."
    await cl.Message(content=f"📝 **Action demandée :** {query}").send()
    await cl.Message(content="🤖 Analyse en cours...").send()
    response = await handle_agent(session_id, query)
    await cl.Message(content=response).send()

@cl.action_callback("send_email")
async def send_email_callback(action):
    session_id = cl.user_session.get("session_id")
    query = "Je souhaite envoyer un email au directeur."
    await cl.Message(content=f"📧 **Action demandée :** {query}").send()
    await cl.Message(content="🤖 Analyse en cours...").send()
    response = await handle_agent(session_id, query)
    await cl.Message(content=response).send()