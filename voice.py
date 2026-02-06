import speech_recognition as sr
from gtts import gTTS
import tempfile
import os

class STTError(Exception):
    """Erreur de reconnaissance vocale avec message utilisateur."""
    pass

def stt_from_audio(audio_file_path: str) -> str:
    r = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio, language="fr-FR")
    except sr.UnknownValueError:
        raise STTError(
            "Parole non reconnue. Parlez plus distinctement, plus proche du micro, "
            "ou vérifiez que le fichier contient bien de la parole (WAV valide)."
        )
    except sr.RequestError as e:
        raise STTError(
            "Service de reconnaissance temporairement indisponible. Réessayez plus tard."
        ) from e

def tts_to_audio(text: str) -> str:
    tts = gTTS(text=text, lang="fr")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name

