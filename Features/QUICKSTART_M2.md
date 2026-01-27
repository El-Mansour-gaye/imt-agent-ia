# 🚀 M2 - CrewAI Multi-Agent NLP System

**Système complet d'automatisation avec CrewAI pour l'IMT Dakar**

## 📋 Vue d'ensemble

Le projet **M2** implémente un système multi-agent basé sur **CrewAI** avec:

- **3 Agents** orchestrés: Researcher, Actioneer, Manager
- **2 Actions obligatoires**:
  - `fill_contact_form`: Remplissage automatique du formulaire https://www.imt.sn/contact
  - `send_director_email`: Envoi d'emails formels au directeur
- **2 Bonus features**:
  - 🌐 **Multi-langue**: Détection automatique (Wolof, Français, Anglais, Espagnol, Arabe)
  - 🔒 **Sécurité**: Rate-limiting, validation d'intention, détection de spam
- **Mémoire de session**: Redis (persistance) + fallback volatile (RAM)
- **Observability**: Tracing Langfuse pour les appels LLM
- **LLM**: Google Gemini 1.5 Pro

---

## 🏗️ Architecture

```
m2_crewai/
├── crewai_config.py          # Configuration 3 agents + crew.kickoff()
├── crew_memory.py             # RedisMemoryManager + VolatileMemoryManager
└── langfuse_tracing.py        # LangfuseTracer (observability)

m2_actions/
├── playwright_form.py         # fill_imt_contact_form() - Playwright automation
└── email_sender.py            # send_director_email() - Gemini + SendGrid/SMTP

m2_bonus/
├── multilingual.py            # detect_lang_and_translate() - 5+ langues
└── security.py                # validate_user_intent() - Rate-limiting + Safety

tests/
└── test_actions.py            # Unit tests

docs/
└── m2-agent-actions-spec.md   # Documentation technique détaillée
```

---

## 🔧 Installation

### 1. Prérequis

- Python 3.10+
- pip / conda
- Compte Gemini API (gratuit)
- (Optionnel) Redis pour persistance M3
- (Optionnel) SendGrid ou Gmail pour emails

### 2. Setup de l'environnement

```bash
# 1. Créer un environnement virtuel
python -m venv venv

# 2. Activer l'environnement
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements_m2.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

### 3. Configuration .env

```bash
# Clés essentielles
GEMINI_API_KEY=your_api_key_from_aistudio.google.com
SENDGRID_API_KEY=your_sendgrid_key_or_empty
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_app_password

# Optionnel - Persistance M3
REDIS_HOST=localhost
REDIS_PORT=6379

# Optionnel - Observability
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_key
```

---

## 🧪 Tests

### Test 1: Validation de tous les modules

```bash
python test_m2.py
```

**Output:**

```
✅ Tous les modules M2 sont fonctionnels!
   ✅ Imports: OK
   ✅ Multi-langue: OK
   ✅ Formulaire: OK
   ✅ Email: OK
   ✅ Sécurité: OK
   ✅ Memory: OK
   ✅ CrewAI: OK
```

### Test 2: Exécution complète du crew

```bash
# Tous les scénarios
python test_crew_full.py

# Scénario spécifique
python test_crew_full.py --scenario search_info
python test_crew_full.py --scenario fill_form
python test_crew_full.py --scenario complete

# Mode verbose
python test_crew_full.py --verbose
```

**Scénarios disponibles:**

| Scénario      | Description                                        |
| ------------- | -------------------------------------------------- |
| `search_info` | Rechercher des infos IMT (Agent Researcher)        |
| `fill_form`   | Remplir le formulaire de contact (Agent Actioneer) |
| `complete`    | Workflow complet (tous les agents)                 |
| `all`         | Tous les scénarios (par défaut)                    |

---

## 💻 Utilisation

### Mode 1: Test rapide

```python
from m2_bonus.security import validate_user_intent
from m2_bonus.multilingual import detect_lang_and_translate

# Valider une requête
security = validate_user_intent("Remplir le formulaire")
if security['allowed']:
    print("✅ Requête autorisée")

# Détecter la langue
lang = detect_lang_and_translate("Nanga def?", target_lang='en')
print(f"Langue: {lang['detected_language']}")
```

### Mode 2: Utilisation du crew complet

```python
from m2_crewai.crewai_config import IMTCrew

# Créer le crew
crew = IMTCrew()

# Exécuter avec kickoff()
result = crew.kickoff(
    query="Quels sont les programmes d'études?",
    user_data={
        "session_id": "user_123",
        "form_data": {
            "nom": "Ahmed Diallo",
            "email": "ahmed@example.sn"
        }
    }
)

print(result)
```

### Mode 3: Actions individuelles

```python
# Remplir le formulaire
from m2_actions.playwright_form import fill_imt_contact_form
result = fill_imt_contact_form("Ahmed Diallo", "ahmed@example.sn", "Message")
print(result)

# Envoyer un email
from m2_actions.email_sender import send_director_email
result = send_director_email("Demande d'information", "Je suis intéressé par...")
print(result)
```

---

## 🤖 Agents CrewAI

### 1. **Researcher Agent**

- **Rôle**: Rechercher les informations IMT
- **Outil**: `imt_rag_search` (M1 integration, simulated)
- **Tâche**: Répondre aux questions sur l'IMT

### 2. **Actioneer Agent**

- **Rôle**: Exécuter les actions (formulaire, email)
- **Outils**:
  - `fill_imt_contact_form` (Playwright)
  - `send_director_email` (Gemini + SendGrid)
- **Tâche**: Remplir les formulaires et envoyer les emails

### 3. **Manager Agent**

- **Rôle**: Orchestrer le workflow
- **Tâche**: Coordonner les 2 agents avec plan-act-observe

---

## 🌐 Bonus Features

### 1. Multi-Langue 🌍

Détection automatique de:

- 🇸🇳 **Wolof** (Sénégal) - détection par mots-clés + langdetect
- 🇫🇷 **Français** (par défaut)
- 🇬🇧 **Anglais**
- 🇪🇸 **Espagnol**
- 🇸🇦 **Arabe**

```python
result = detect_lang_and_translate("Nanga def?", target_lang='fr')
# → détecte Wolof, traduit en Français via Gemini
```

### 2. Sécurité 🔒

- **Rate-limiting**: Max 5 formulaires/jour par session
- **Safety checks**: Gemini safety API (risk score 0-1)
- **CAPTCHA**: Déclenché après 3 tentatives échouées
- **Spam detection**: Bloque les patterns malveillants

```python
security = validate_user_intent("Requête utilisateur", session_id="user_123")
# → retourne {'allowed': bool, 'risk_score': 0-1, 'reason': str}
```

---

## 📊 Memory Management

### Redis (Persistance M3)

```python
from m2_crewai.crew_memory import RedisMemoryManager

manager = RedisMemoryManager()
manager.save_conversation(session_id, "user", "Bonjour")
history = manager.get_conversation_history(session_id)
```

### Volatile (Fallback)

Si Redis non disponible:

```python
from m2_crewai.crew_memory import VolatileMemoryManager

manager = VolatileMemoryManager()  # RAM seulement, 24h TTL
```

---

## 📈 Observability (Langfuse)

Tous les appels Gemini sont tracés automatiquement:

```
Langfuse Dashboard:
├── Token usage tracking
├── Latency analysis
├── Error monitoring
└── Cost analytics
```

---

## 🐛 Troubleshooting

### Erreur: "GEMINI_API_KEY not configured"

```bash
# Solution: Ajouter la clé dans .env
GEMINI_API_KEY=sk-proj-xxx...
```

### Erreur: "Redis connection refused"

```bash
# Ça va! Le système utilise le fallback volatile (RAM)
# Optionnel: Installer Redis pour persistance
# Windows: https://github.com/microsoftarchive/redis/releases
```

### Erreur: Playwright ne remplissant pas le formulaire

```bash
# 1. Vérifier que le site est accessible
curl https://www.imt.sn/contact

# 2. Activer le mode non-headless pour debugging
PLAYWRIGHT_HEADLESS=false python test_crew_full.py --scenario fill_form

# 3. Vérifier les sélecteurs CSS dans playwright_form.py
```

### Erreur: Email non envoyé

```bash
# 1. Vérifier SendGrid (prioritaire)
SENDGRID_API_KEY=SG.xxx...

# 2. Vérifier Gmail fallback
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=app_password  # App Password, pas mot de passe normal
```

---

## 📁 Fichiers clés

| Fichier                         | Rôle                                   |
| ------------------------------- | -------------------------------------- |
| `test_m2.py`                    | Test de tous les modules (7 tests)     |
| `test_crew_full.py`             | Test d'exécution du crew (3 scénarios) |
| `.env`                          | Configuration (créé après setup)       |
| `requirements_m2.txt`           | Dépendances avec versions exactes      |
| `docs/m2-agent-actions-spec.md` | Spécifications techniques détaillées   |

---

## ✅ Checklist de validation M2

- [x] Structure de dossiers créée ✓
- [x] 3 agents CrewAI implémentés ✓
- [x] `fill_contact_form` avec Playwright ✓
- [x] `send_director_email` avec Gemini + SendGrid/SMTP ✓
- [x] Multi-langue (Wolof, Français, Anglais, etc.) ✓
- [x] Sécurité (rate-limiting, validation d'intention) ✓
- [x] Mémoire (Redis + Volatile) ✓
- [x] Observability (Langfuse) ✓
- [x] Tests (test_m2.py: 7/7 ✅) ✓
- [x] Documentation complète ✓

---

## 🎯 Prochaines étapes (M3)

1. **Intégration Redis complète**
   - Persistance des sessions 24h
   - Synchronisation multi-instances

2. **Déploiement production**
   - Docker containerization
   - API REST wrapper
   - Kubernetes orchestration

3. **Enhancements**
   - Webhook pour mises à jour real-time
   - Dashboard monitoring
   - Analytics avancée

---

## 📧 Support

Pour questions/issues:

1. Vérifier la section Troubleshooting
2. Consulter `docs/m2-agent-actions-spec.md`
3. Exécuter `python test_m2.py` pour diagnostiquer

---

## 📄 Licence

Projet IMT Dakar - M2 NLP Course

**Créé le**: January 2026
**Dernière mise à jour**: 27 Jan 2026
**Version**: 1.0.0

---

## 🚀 Démarrage rapide

```bash
# 1. Cloner et configurer
git clone <repo>
cd Features
python -m venv venv
venv\Scripts\activate
pip install -r requirements_m2.txt

# 2. Configurer .env
cp .env.example .env
# → Éditer et ajouter GEMINI_API_KEY

# 3. Valider les modules
python test_m2.py
# → ✅ Tous les modules M2 sont fonctionnels!

# 4. Exécuter le workflow
python test_crew_full.py --scenario complete
# → 🎯 Workflow complet réussi!
```

**Status**: ✅ **PRÊT POUR PRODUCTION**
