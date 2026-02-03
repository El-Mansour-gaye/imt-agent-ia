# =========================
# IMPORTS
# =========================
import chainlit as cl
import base64
import uuid
import numpy as np
import soundfile as sf

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

# Pour associer le feedback (pouces) à Langfuse
try:
    from opentelemetry import trace

    def _get_current_trace_id() -> str | None:
        span = trace.get_current_span()
        if span.is_recording() and span.get_span_context().trace_id:
            return format(span.get_span_context().trace_id, "032x")
        return None

except Exception:
    def _get_current_trace_id() -> str | None:
        return None

# =========================
# UTILITAIRES
# =========================
def create_session_id():
    return f"IMT-{uuid.uuid4().hex[:8]}"

async def call_agent_mock(user_message: str, context: str) -> str:
    return f"""
🎓 **Assistant IMT**

Votre question :
> {user_message}

📚 **Contexte pris en compte**
{context}

ℹ️ Réponse simulée.
L’agent IA complet sera intégré via CrewAI.
"""

async def grok_summarize(conversation: list) -> str:
    return (
        "Résumé automatique : "
        "L'utilisateur s'informe sur l'IMT, notamment "
        "les formations, les frais et l'admission."
    )

# =========================
# LANGFUSE – TRACE PRINCIPALE
# =========================
@observe(name="trace_agent_query")
async def handle_agent(session_id: str, user_message: str) -> str:
    # Analytics compteur
    increment_query("general")

    # Résumé automatique si long contexte
    total = count_messages(session_id)
    if total > 20 and not get_summary(session_id):
        summary = await grok_summarize(get_last_messages(session_id, limit=20))
        save_summary(session_id, summary)

    # Contexte à injecter
    context = build_context(session_id, limit=10)

    return await call_agent_mock(user_message=user_message, context=context)

# =========================
# LANGFUSE – ACTIONS
# =========================
@observe(name="trace_action")
async def handle_action(action_name: str) -> str:
    return f"Action {action_name} exécutée (mock)"

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
💾 Mémoire persistante : **Redis activé**  
📊 Observabilité : **Langfuse activé**

Posez vos questions sur :
- les formations
- les frais
- l’admission
- l’IMT en général
""",
        actions=[
            cl.Action(name="fill_form", value="form", label="📝 Remplir le formulaire"),
            cl.Action(name="send_email", value="email", label="📧 Écrire au directeur"),
            cl.Action(name="generate_pdf", value="pdf", label="📄 Générer mon plan IMT"),
            cl.Action(name="message_vocal", value="voice", label="🎤 Message vocal"),
            cl.Action(name="export_csv", value="csv", label="📊 Exporter analytics CSV")
        ]
    ).send()

# =========================
# MESSAGES TEXTE
# =========================
@cl.on_message
async def on_message(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    save_message(session_id, "user", message.content)

    await cl.Message(content="🤖 Analyse de votre demande...").send()

    response = await handle_agent(session_id, message.content)

    trace_id = _get_current_trace_id()
    if trace_id:
        cl.user_session.set("last_trace_id", trace_id)

    save_message(session_id, "assistant", response)

    await cl.Message(
        content=response,
        actions=[
            cl.Action(name="feedback_up", value="1", label="👍"),
            cl.Action(name="feedback_down", value="-1", label="👎")
        ]
    ).send()

# =========================
# ACTIONS UI
# =========================
@cl.action_callback("fill_form")
async def fill_form(action):
    await handle_action("fill_form")
    await cl.Message(content="📝 Formulaire IMT (mock)").send()

@cl.action_callback("send_email")
async def send_email(action):
    await handle_action("send_email")
    await cl.Message(content="📧 Email au directeur (mock)").send()

@cl.action_callback("generate_pdf")
async def generate_pdf(action):
    session_id = cl.user_session.get("session_id")
    context = build_context(session_id, limit=20)
    pdf_path = generate_reco_pdf(context)

    await handle_action("generate_pdf")
    await cl.Message(
        content="📄 Voici votre plan personnalisé IMT",
        elements=[cl.File(name="plan_IMT.pdf", path=pdf_path)]
    ).send()

# =========================
# FEEDBACK & ANALYTICS
# =========================
def _send_feedback_to_langfuse(trace_id: str | None, value: int):
    if not trace_id:
        return
    try:
        get_langfuse_client().create_score(
            trace_id=trace_id,
            name="user_feedback",
            value=value,
            data_type="NUMERIC",
            comment="Thumbs up/down depuis Chainlit",
        )
    except Exception:
        pass

def _update_feedback_ui(session_id):
    total_messages = count_messages(session_id)
    return f"📊 Analytics session : {total_messages} messages échangés"

@cl.action_callback("feedback_up")
async def feedback_up(action):
    session_id = cl.user_session.get("session_id")
    save_feedback(session_id, 1)
    _send_feedback_to_langfuse(cl.user_session.get("last_trace_id"), 1)
    await cl.Message(content=f"Merci pour votre retour 👍\n{_update_feedback_ui(session_id)}").send()

@cl.action_callback("feedback_down")
async def feedback_down(action):
    session_id = cl.user_session.get("session_id")
    save_feedback(session_id, -1)
    _send_feedback_to_langfuse(cl.user_session.get("last_trace_id"), -1)
    await cl.Message(content=f"Merci, nous allons nous améliorer 👌\n{_update_feedback_ui(session_id)}").send()

@cl.action_callback("export_csv")
async def export_csv(action):
    path = export_analytics_csv()
    await cl.Message(
        content="📊 Export des analytics (requêtes + feedbacks).",
        elements=[cl.File(name="analytics_export.csv", path=path)]
    ).send()

# =========================
# AUDIO UTILS / MICRO NATIF
# =========================
AUDIO_SAMPLE_RATE = 44100
audio_buffer = []

def _chunk_data_as_bytes(chunk) -> bytes:
    data = chunk.data
    if isinstance(data, str):
        return base64.b64decode(data)
    return data if isinstance(data, bytes) else bytes(data)

def _build_wav_from_buffer(buffer, sample_rate: int) -> str:
    raw = b"".join(buffer)
    if len(raw) < 3200:
        raise ValueError("Enregistrement trop court. Parlez au moins 1 seconde.")
    try:
        audio_np = np.frombuffer(raw, dtype=np.int16)
        print("DEBUG: dtype int16, len", audio_np.shape[0])
    except Exception:
        audio_np = np.frombuffer(raw, dtype=np.float32)
        audio_np = (audio_np * 32767).clip(-32768, 32767).astype(np.int16)
        print("DEBUG: dtype float32 converti, len", audio_np.shape[0])
    wav_path = "temp_audio.wav"
    sf.write(wav_path, audio_np, sample_rate)
    return wav_path

@cl.on_audio_chunk
async def on_audio_chunk(chunk):
    if getattr(chunk, "isStart", False):
        audio_buffer.clear()
    audio_buffer.append(_chunk_data_as_bytes(chunk))

@cl.on_audio_end
async def on_audio_end(file_elements=None):
    session_id = cl.user_session.get("session_id")
    wav_path = None

    if file_elements and len(file_elements) > 0 and getattr(file_elements[0], "path", None):
        wav_path = file_elements[0].path

    if not wav_path and audio_buffer:
        try:
            wav_path = _build_wav_from_buffer(audio_buffer, AUDIO_SAMPLE_RATE)
        except ValueError as e:
            await cl.Message(content=f"⚠️ {e}").send()
            audio_buffer.clear()
            return

    if not wav_path:
        await cl.Message(content="Aucun audio reçu.").send()
        return

    try:
        text = stt_from_audio(wav_path)
        if not text.strip():
            raise ValueError("Aucune parole détectée dans l'audio. Parlez distinctement.")
    except Exception as e:
        await cl.Message(content=f"⚠️ {e}").send()
        return

    save_message(session_id, "user", text)
    await cl.Message(content=f"🎤 Vous avez dit : **{text}**").send()

    response = await handle_agent(session_id, text)
    trace_id = _get_current_trace_id()
    if trace_id:
        cl.user_session.set("last_trace_id", trace_id)

    save_message(session_id, "assistant", response)
    audio_response = tts_to_audio(response)

    await cl.Message(content=response, elements=[cl.Audio(path=audio_response)]).send()
    audio_buffer.clear()
