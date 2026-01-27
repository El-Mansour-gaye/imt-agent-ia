# M2 - Orchestration Agent & Actions

## Spécifications Complètes

---

## 📋 Vue d'ensemble M2

**Responsabilité**: Orchestration multi-agent (CrewAI) avec actions pratiques (formulaires, emails) et bonus (multi-langue, sécurité).

### Composants Clés

```
┌─────────────────────────────────────────────────┐
│           CrewAI Crew Orchestrator              │
├─────────────────────────────────────────────────┤
│  Manager (Gemini 1.5 Pro)                       │
│  ├─ Planification & Raisonnement                │
│  └─ Plan-Act-Observe cycle                      │
│                                                 │
│  Researcher Agent (RAG M1)                      │
│  ├─ Tool: imt_rag_search(query)                │
│  └─ Source: IMT knowledge base                  │
│                                                 │
│  Actioneer Agent (Automations)                  │
│  ├─ Tool: fill_imt_contact_form()              │
│  ├─ Tool: send_director_email()                │
│  └─ [BONUS] Tool: validate_user_intent()       │
│                                                 │
│  Memory: Redis (M3) + Volatile fallback         │
│  Tracing: Langfuse observability                │
│  [BONUS] Multi-langue & Rate-Limiting          │
└─────────────────────────────────────────────────┘
```

---

## 🤖 Configuration Agents

### 1. Manager Agent (Gemini 1.5 Pro)

```python
manager = Agent(
    role="Directeur Orchestration IMT",
    goal="Coordonner agents pour tâches complexes",
    backstory="Expert planification et supervision",
    llm=Gemini15Pro,
    allow_delegation=True,
    verbose=True
)
```

### 2. Researcher Agent

```python
researcher = Agent(
    role="Chercheur Expert IMT",
    goal="Recherche informations précises via RAG",
    backstory="Spécialiste base données IMT",
    tools=[imt_rag_search],  # De M1
    llm=Gemini15Pro
)
```

### 3. Actioneer Agent

```python
actioneer = Agent(
    role="Assistant Automations",
    goal="Exécuter actions concrètes",
    backstory="Spécialiste web & email",
    tools=[fill_contact_form, send_director_email],
    llm=Gemini15Pro
)
```

---

## ✅ Outils Obligatoires M2

### 1️⃣ fill_imt_contact_form()

**Fichier**: `m2_actions/playwright_form.py`

```python
fill_imt_contact_form(
    nom: str,
    email: str,
    message: str,
    telephone: str = None,
    url: str = "https://www.imt.sn/contact",
    screenshot_dir: str = "screenshots"
) -> Dict[str, Any]
```

**Retour**:

```python
{
    "status": "success",
    "screenshot_path": "screenshots/contact_form_...png",
    "timestamp": "2026-01-27T14:30:22",
    "logs": ["✅ Formulaire rempli", "✅ Screenshot sauvegardé"]
}
```

**Features**:

- ✅ Détecte sélecteurs dynamiquement
- ✅ Rempli (nom, email, téléphone, message)
- ✅ Soumet formulaire
- ✅ Screenshot proof
- ✅ Logs complets

---

### 2️⃣ send_director_email()

**Fichier**: `m2_actions/email_sender.py`

```python
send_director_email(
    user_request: str,
    user_name: str = "Utilisateur",
    context: Dict[str, Any] = None
) -> Dict[str, Any]
```

**Processus**:

1. Gemini génère email formel
2. Extraction subject/body/to
3. Template HTML professionnel
4. Envoi SendGrid ou SMTP Gmail

---

## 🎁 Outils Bonus M2

### 📱 detect_lang_and_translate()

**Fichier**: `m2_bonus/multilingual.py`

```python
detect_lang_and_translate(
    query: str,
    target_lang: str = 'fr'
) -> Dict[str, Any]
```

**Support**: Wolof 🇸🇳 / Français 🇫🇷 / Anglais 🇬🇧

**Exemple**:

```python
# Input Wolof
result = detect_lang_and_translate("Nanga def? Mangi xam frais yi")

# Output
{
    'detected_language': 'wo',
    'confidence': 0.85,
    'translated_text': "Comment allez-vous? Je veux savoir les frais"
}
```

---

### 🔒 validate_user_intent()

**Fichier**: `m2_bonus/security.py`

```python
validate_user_intent(
    query: str,
    session_id: str = "default"
) -> Dict[str, Any]
```

**Features**:

- ✅ Safety check Gemini (risk score)
- ✅ Rate-limiting Redis (>5 forms/jour → block)
- ✅ CAPTCHA audio simulation

---

## 🧠 Memory & Tracing

### Redis (M3)

```python
memory = RedisMemoryManager()
memory.store("session:user123", data, ttl=86400)
```

### Langfuse

```python
tracer = LangfuseTracer()
tracer.start_span("fill_form", {"nom": "Mamadou"})
# ... execution ...
tracer.end_span("fill_form", {"status": "success"})
```

---

## 🔄 Exemple Complet: Cas d'Usage

### Requête

```
"Je suis intéressé par ISI, remplis le formulaire"
```

### Process

```
1. Manager: Planifie recherche + formulaire
2. Researcher: Recherche "ISI" via imt_rag_search()
3. Security: validate_user_intent() → OK
4. Language: detect_lang_and_translate() → Français OK
5. Actioneer: fill_imt_contact_form() → ✅ Screenshot
6. Memory: Redis stocke session (24h)
7. Tracing: Langfuse enregistre spans
```

---

## 📦 Dependencies

```
crewai==0.51.2
playwright==1.47.0
sendgrid==6.10.0
langdetect==1.0.9
redis>=5.1.0
langfuse>=2.17.0
google-generativeai>=0.8.3
```

---

**Version**: 1.0.0  
**Status**: ✅ Complet  
**Last Update**: 27/01/2026
