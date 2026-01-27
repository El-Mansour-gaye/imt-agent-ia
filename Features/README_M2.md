# 🚀 M2 - Orchestration Agent & Actions IMT

## CrewAI Setup + Actions + Bonus Multi-Langue & Sécurité

---

## 📌 Responsabilité M2 (selon plan)

Setup CrewAI avec **3 agents collaboratifs** + **2 outils obligatoires** + **2 bonus** haute qualité:

```
Cas d'usage: "Explique frais ISI puis remplis le formulaire"
             ↓
          Manager (Gemini 1.5 Pro) planifie
             ↓
    Researcher (RAG M1) + Actioneer (Actions)
             ↓
  fill_contact_form() ✅ + send_email() ✅
             ↓
detect_lang & rate-limiting (BONUS) ✅
```

---

## ✅ Tâches Obligatoires M2

### 1. Setup CrewAI

- ✅ **3 agents**: Researcher (imt_rag_search de M1), Actioneer (tools), Manager (Gemini 1.5 Pro)
- ✅ **Processus crew.kickoff(query)** avec mémoire Redis (M3) et traces Langfuse
- ✅ **Justification**: Multi-agents > single LLM pour tâches complexes

### 2. Outil: fill_contact_form

- ✅ **Playwright** pour détecter/remplir champs https://www.imt.sn/contact
- ✅ **Champs**: nom, email, téléphone, message
- ✅ **Submit + Screenshot proof** + log succès/échec
- ✅ **Selectors dynamiques** via LLM si needed

### 3. Outil: send_director_email

- ✅ **Générateur email** formel via Gemini prompt "Rédige email Directeur IMT: {user_request}"
- ✅ **Extraction**: to/sujet/body
- ✅ **Envoi**: SMTP Gmail/SendGrid avec **template pro** (signature IMT)

---

## 🎁 Tâches Bonus M2 (Haute qualité)

### Multi-langue Detection/Traduction

- ✅ `detect_lang_and_translate(query)` → Wolof/Français/Anglais via langdetect
- ✅ **Traduction** → Français via Gemini
- ✅ **Réponses bilingues**: "Formation ISI (AI program): 2M CFA"
- ✅ **Justification**: Inclusif Dakar, +30% users potentiels (internationaux)

### Sécurité & Rate-Limiting

- ✅ `validate_user_intent(risk_score)` → Gemini safety check
- ✅ **Redis counters**: user_attempts:session_id
- ✅ **Spam block**: >5 forms/jour
- ✅ **CAPTCHA simu audio** si Playwright détecte
- ✅ **Justification**: Production-ready, appréciée des profs (éthique)

---

## 🏗️ Structure du Projet

```
FEATURES/
├── m2_crewai/
│   ├── __init__.py
│   ├── crewai_config.py          # ✅ Agents CrewAI + crew.kickoff()
│   ├── crew_memory.py            # ✅ RedisMemoryManager + VolatileMemoryManager
│   └── langfuse_tracing.py       # ✅ LangfuseTracer
│
├── m2_actions/
│   ├── __init__.py
│   ├── action_tools.py           # ✅ CrewAI tools definitions
│   ├── playwright_form.py        # ✅ fill_imt_contact_form()
│   └── email_sender.py           # ✅ send_director_email()
│
├── m2_bonus/
│   ├── __init__.py
│   ├── multilingual.py           # ✅ detect_lang_and_translate()
│   └── security.py               # ✅ validate_user_intent() + rate-limiting
│
├── tests/
│   └── test_actions.py           # Tests unitaires
│
├── docs/
│   ├── m2-agent-actions-spec.md  # Spécifications techniques
│   └── m2-agent-actions.md       # Documentation complète
│
├── requirements_m2.txt           # ✅ crewai==0.51.2, etc
├── .env.example                  # ✅ GEMINI_API_KEY, SENDGRID_API_KEY
└── README_M2.md                  # Ce fichier
```

---

## 🔧 Installation Rapide

### 1. Virtual Environment

```bash
cd Features

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 2. Dépendances

```bash
pip install -r requirements_m2.txt

# Playwright browsers (OBLIGATOIRE pour fill_form)
playwright install chromium
```

### 3. Configuration .env

```bash
cp .env.example .env

# OBLIGATOIRE à remplir:
# GEMINI_API_KEY=your_key_here
# SENDGRID_API_KEY=SG_...
# GMAIL_EMAIL=your-email@gmail.com
# GMAIL_PASSWORD=app_password
# REDIS_HOST=localhost (optionnel si Redis disponible)
```

### 4. Redis (Recommandé pour M3)

```bash
# Option 1: Local
redis-server  # ou via docker

# Option 2: Fallback automatique à VolatileMemoryManager
```

---

## 🚀 Usage - Exemples Pratiques

### Exemple 1: Crew Complet (Recherche + Formulaire)

```python
from m2_crewai.crewai_config import IMTCrewSetup

# Initialiser crew avec session
crew = IMTCrewSetup(session_id="user_123", use_redis=True)

# Exécuter query complexe
result = crew.kickoff({
    "query": "Explique les frais ISI puis remplis le formulaire",
    "user_data": {
        "nom": "Mamadou Sall",
        "email": "mamadou@example.com",
        "telephone": "+221 77 123 45 67",
        "message": "Je suis intéressé par ISI"
    }
})

# Résultats
print(result["response"])           # Réponse textuelle complète
print(result["actions_completed"])  # Actions effectuées
print(result["session_id"])         # Session ID
```

### Exemple 2: Multi-langue Bonus

```python
from m2_bonus.multilingual import detect_lang_and_translate

# Input Wolof (Dakar)
result = detect_lang_and_translate("Nanga def? Mangi xam frais yi ci ISI")

print(f"Langue détectée: {result['detected_language_name']}")
print(f"Traduit: {result['translated_text']}")

# Output:
# Langue détectée: wolof
# Traduit: Comment allez-vous? Je veux savoir les frais chez ISI
```

### Exemple 3: Sécurité & Rate-Limiting Bonus

```python
from m2_bonus.security import validate_user_intent

# Vérifier si requête est autorisée
result = validate_user_intent(
    query="Remplis le formulaire contact",
    session_id="user_123"
)

if result["allowed"]:
    print("✅ Requête autorisée")
    print(f"Rate limit: {result['rate_limit']['current']}/{result['rate_limit']['max']}")
else:
    print(f"❌ Bloqué: {result['reason']}")
    # (exemple: "Trop de requêtes. Limite 5 forms/jour atteinte")
```

---

## 🤖 Configuration Agents CrewAI (Plan M2)

### 1. Manager Agent (Gemini 1.5 Pro)

```python
# Role: Directeur Orchestration IMT
# Goal: Coordonner agents pour résoudre requête complexe
# Responsibility: Planifier (plan-act-observe)
# LLM: gemini-1.5-pro
```

**Tâche**: Analyser query → Planifier actions → Superviser exécution

### 2. Researcher Agent (avec M1 RAG)

```python
# Role: Chercheur Expert IMT
# Goal: Trouver infos précises via RAG
# Tool: imt_rag_search() de M1
# LLM: gemini-1.5-pro
```

**Output**: Informations structurées avec sources

### 3. Actioneer Agent (Outils Actions)

```python
# Role: Assistant Actions Automatisées
# Goal: Exécuter actions concrètes
# Tools: fill_contact_form, send_director_email
# LLM: gemini-1.5-pro
```

**Responsabilité**: Remplir formulaires, envoyer emails

---

## ✅ Outils Obligatoires M2

### Tool 1: fill_imt_contact_form()

**Fichier**: `m2_actions/playwright_form.py::fill_imt_contact_form()`

```python
from m2_actions.playwright_form import fill_imt_contact_form

result = fill_imt_contact_form(
    nom="Jean Dupont",
    email="jean@example.com",
    telephone="+221771234567",
    message="Intéressé par ISI"
)

# Retour:
{
    "status": "success",
    "screenshot_path": "screenshots/contact_form_20260127_143022.png",
    "timestamp": "2026-01-27T14:30:22",
    "logs": ["✅ Page chargée", "✅ Champs remplis", "✅ Formulaire soumis"]
}
```

**Spécifications**:

- ✅ Target URL: https://www.imt.sn/contact
- ✅ Détection de sélecteurs dynamiquement
- ✅ Rempli: nom, email, téléphone, message
- ✅ Soumet formulaire
- ✅ Screenshot proof sauvegardé
- ✅ Log complet succès/échec

---

### Tool 2: send_director_email()

**Fichier**: `m2_actions/email_sender.py::send_director_email()`

```python
from m2_actions.email_sender import send_director_email

result = send_director_email(
    user_request="Je suis intéressé par la formation ISI",
    user_name="Ahmed Sall"
)

# Retour:
{
    "status": "success",
    "message": "Email envoyé avec succès à directeur@imt.sn",
    "subject": "Demande d'information: Formation ISI",
    "message_id": "sg_msg_abc123..."
}
```

**Processus**:

1. **Gemini génère** email formel: "Rédige email Directeur IMT: {user_request}"
2. **Extraction**: to_email, subject, body
3. **Template HTML** professionnel (signature IMT)
4. **Envoi**: SendGrid API (priorité) ou SMTP Gmail (fallback)

---

## 🎁 Outils Bonus M2 (Haute Qualité)

### Bonus 1: Multi-langue (detect_lang_and_translate)

```python
from m2_bonus.multilingual import detect_lang_and_translate

# Support: Wolof 🇸🇳 / Français 🇫🇷 / Anglais 🇬🇧 / Espagnol / Arabe
result = detect_lang_and_translate(
    query="Nanga def?",  # Wolof pour "Comment allez-vous?"
    target_lang='fr'     # Traduire en français
)

# Retour:
{
    'detected_language': 'wo',
    'detected_language_name': 'wolof',
    'confidence': 0.85,
    'original_text': "Nanga def?",
    'translated_text': "Comment allez-vous?",
    'is_translated': True
}
```

**Justification**: Inclusif Dakar (multilingue) → +30% utilisateurs potentiels

### Bonus 2: Sécurité & Rate-Limiting (validate_user_intent)

```python
from m2_bonus.security import validate_user_intent

result = validate_user_intent(
    query="Remplir le formulaire contact",
    session_id="user_123"
)

# Retour:
{
    'allowed': True,  # Ou False si bloqué
    'risk_score': 0.15,  # Confiance sécurité [0-1]
    'reason': "Intent is legitimate",
    'rate_limit': {
        'current': 2,
        'max': 5,
        'period': 'day',
        'remaining': 3
    },
    'requires_captcha': False
}
```

**Features**:

- ✅ **Safety Check Gemini**: Analyse risque [0-1]
- ✅ **Rate Limiting Redis**: Max 5 forms/jour, 10 requêtes/heure
- ✅ **Auto-block**: >5 forms → blocage 1h
- ✅ **CAPTCHA Audio**: Simulation après 3 échecs

**Justification**: Production-ready, apprécié profs (éthique + sécurité)

---

## 🧠 Memory & Observability

### Memory: Redis (M3 Integration)

```python
from m2_crewai.crew_memory import RedisMemoryManager

manager = RedisMemoryManager()
manager.store("session:user123:query", data, ttl=86400)  # 24h TTL
data = manager.retrieve("session:user123:query")
```

**Fallback**: VolatileMemoryManager (RAM) si Redis non disponible

### Tracing: Langfuse

```python
from m2_crewai.langfuse_tracing import LangfuseTracer

tracer = LangfuseTracer()
tracer.start_span("fill_form", {"nom": "Mamadou"})
# ... exécution ...
tracer.end_span("fill_form", {"status": "success"})

# Dashboard: https://cloud.langfuse.com
```

---

## 🔄 Workflow Complet: Exemple Cas d'Usage

### Requête

```
"Je suis intéressé par ISI, remplis le formulaire contact"
```

### Processus crew.kickoff()

```
1. Manager (Gemini)
   ├─ Parse: "Recherche ISI" + "Formulaire à remplir"
   └─ Plan: Researcher → Actioneer

2. Researcher (imt_rag_search)
   ├─ Query: "Formation ISI details"
   └─ Result: [{"content": "ISI est...", "score": 0.95, ...}]

3. Manager (Raisonnement)
   └─ "Formulaire requis" → Delegate Actioneer

4. Actioneer (fill_imt_contact_form)
   ├─ Playwright: Navigue https://www.imt.sn/contact
   ├─ Rempli: nom, email, téléphone, message
   ├─ Submit
   └─ Screenshot: /screenshots/contact_form_...png ✅

5. Security (validate_user_intent) [BONUS]
   ├─ Gemini: Risk score = 0.1 (safe)
   ├─ Redis: Rate limit OK (2/5 forms today)
   └─ Result: allowed=True ✅

6. Language (detect_lang_and_translate) [BONUS]
   ├─ Input Français → No translation needed
   └─ Response: Bilingue si output Wolof

7. Memory (RedisMemoryManager - M3)
   ├─ Store: session:user123:query (24h TTL)
   ├─ Store: task_history:user123 (7d TTL)
   └─ Export: /memory/session_user123.json

8. Tracing (Langfuse)
   ├─ Span: researcher_search (500ms)
   ├─ Span: fill_form (2.3s)
   └─ Dashboard: cloud.langfuse.com ✅

OUTPUT:
{
  "response": "Merci! Formulaire envoyé. ISI: 2 ans, 1.85M FCFA",
  "actions_completed": [
    {step: 1, action: "research_imt", status: "success"},
    {step: 2, action: "fill_contact_form", status: "success"}
  ],
  "session_id": "user_123",
  "memory_file": "memory/session_user_123.json"
}
```

---

## 🧪 Tests

### Unit Tests

```bash
pytest tests/test_actions.py -v
```

### Integration Test: Crew Complet

```bash
python -c "
from m2_crewai.crewai_config import IMTCrewSetup
crew = IMTCrewSetup(session_id='test_123')
result = crew.kickoff({
    'query': 'Quels sont les frais ISI?',
    'user_data': {'nom': 'Test User', 'email': 'test@ex.com'}
})
print('✅ Test réussi!' if 'response' in result else '❌ Test échoué')
"
```

---

## 📦 Dependencies (Plan M2)

```
crewai==0.51.2
playwright==1.47.0
sendgrid==6.10.0
langdetect==1.0.9
langfuse>=2.17.0
google-generativeai>=0.8.3
redis>=5.1.0
python-dotenv>=1.0.1
pydantic>=2.0.0
```

---

## 🎯 Git Branches & Commits (Plan M2)

### Branches

```
feature/m2-crewai          # Agents CrewAI + processus principal
feature/m2-actions-oblig   # fill_contact_form + send_email
feature/m2-multi-lang      # Multi-langue + sécurité (bonus)
```

### Commits Exemple (Daily Pull develop!)

```bash
git commit -m "M2: Add CrewAI Researcher+Actioneer avec Gemini Manager"
git commit -m "M2: Fix Playwright selectors contact form + screenshot proof"
git commit -m "M2: Add langdetect Wolof→Français pour queries inclusives"
git commit -m "M2: Implement rate-limiting Redis >5 forms/jour"
```

---

## 🔐 Environment Variables

### Obligatoires

```
GEMINI_API_KEY=sk_xxx                   # Google AI Studio
SENDGRID_API_KEY=SG_xxx                 # SendGrid dashboard
GMAIL_EMAIL=your-email@gmail.com        # SMTP Gmail (fallback)
GMAIL_PASSWORD=app_specific_password    # App password
```

### Optionnels (Recommandé)

```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=                         # Si authentification
LANGFUSE_PUBLIC_KEY=pk_xxx
LANGFUSE_SECRET_KEY=sk_xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## ⚠️ Troubleshooting

| Problème                 | Solution                                              |
| ------------------------ | ----------------------------------------------------- |
| GEMINI_API_KEY manquante | Vérifier `.env` et remplir depuis Google AI Studio    |
| Playwright timeout       | `playwright install chromium --with-deps`             |
| Redis non disponible     | Fallback auto à VolatileMemoryManager (RAM)           |
| SendGrid erreur          | Vérifier clé API + rate limits, fallback à SMTP Gmail |
| Formulaire non rempli    | Vérifier selectors avec `browser.console.log()`       |

---

## 📚 Documentation

- **Specs Techniques**: [docs/m2-agent-actions-spec.md](docs/m2-agent-actions-spec.md)
- **API Reference**: [docs/m2-agent-actions.md](docs/m2-agent-actions.md)
- **Code Source**: Voir fichiers Python commentés

---

## 🎓 Planning M2 (5-7 jours)

| Jour   | Tâche                | Détails                               |
| ------ | -------------------- | ------------------------------------- |
| **J1** | CrewAI skeleton      | Agents vides, mock tools              |
| **J2** | M1 RAG + fill_form   | Intégrer imt_rag_search, Playwright   |
| **J3** | send_email + PR      | SendGrid/SMTP, PR develop             |
| **J4** | Multi-langue bonus   | detect_lang_and_translate (Wolof/FR)  |
| **J5** | Rate-limiting + Docs | Rate-limit Redis, m2-agent-actions.md |

---

## ✨ Highlights M2

✅ **Production-Ready**: Error handling, fallbacks, rate-limiting  
✅ **Inclusif**: Support Wolof + Français + Anglais  
✅ **Observable**: Langfuse tracing + logs détaillés  
✅ **Persistent**: Redis memory (M3) + JSON exports  
✅ **Sécurisé**: Gemini safety checks + input validation  
✅ **Scalable**: Multi-agent architecture, delegation support

---

## 🤝 Integration Points (Multi-M)

- **M1 (RAG)**: `imt_rag_search()` importée dans Researcher agent
- **M3 (Redis)**: RedisMemoryManager pour sessions persistantes (24h TTL)
- **M4 (Frontend)**: API REST expose `crew.kickoff()`

---

**Version**: 1.0.0  
**Status**: ✅ Complet & Opérationnel  
**Responsible**: M2 Team  
**Last Update**: 27/01/2026

---

## 🚀 Quick Reference

```python
# Main import
from m2_crewai.crewai_config import IMTCrewSetup

# Usage complet
crew = IMTCrewSetup(session_id="user_123", use_redis=True)
result = crew.kickoff({
    "query": "Explique frais ISI",
    "user_data": {"nom": "...", "email": "..."}
})

# Multi-langue [BONUS]
from m2_bonus.multilingual import detect_lang_and_translate
detect_lang_and_translate("Nanga def?")  # Wolof support

# Sécurité [BONUS]
from m2_bonus.security import validate_user_intent
validate_user_intent("query", session_id="user_123")
```

---

## 📞 Support & Questions

- Voir **docs/m2-agent-actions-spec.md** pour spécifications détaillées
- Review **tests/test_actions.py** pour exemples
- Check **.env.example** pour configuration

**Bon coding! 🎉**
