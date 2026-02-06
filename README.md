# IMT Agent IA - Assistant Intelligent pour l'IMT Dakar

Ce projet est un agent conversationnel intelligent conçu pour l'Institut des Métiers des Télécommunications (IMT) de Dakar. Il combine le Scraping, le RAG (Retrieval-Augmented Generation) et des actions automatisées pour répondre aux questions des étudiants et futurs étudiants.

## 🚀 Architecture Globale

- **Backend Data Pipeline (M1)**: Scraping du site imt.sn avec Scrapy, indexation dans ChromaDB avec Gemini Embeddings.
- **Agent Core & Actions (M2)**: Orchestration CrewAI avec 3 agents (Researcher, Actioneer, Manager). Outils d'action avec Playwright (formulaires) et SMTP/SendGrid (emails).
- **UI & Observability (M3)**: Interface web Chainlit, mémoire persistante Redis, et monitoring complet avec Langfuse.

## 🛠️ Installation et Setup

### 1. Cloner le repository
```bash
git clone https://github.com/votre-equipe/imt-agent-ia.git
cd imt-agent-ia
```

### 2. Configuration de l'environnement
```bash
cp .env.example .env
# Remplissez les clés nécessaires, notamment GEMINI_API_KEY
```

### 3. Lancer les services (Docker)
```bash
docker-compose up -d
```

### 4. Installer les dépendances
```bash
pip install -r requirements.txt
playwright install chromium
```

### 5. Préparer les données (Optionnel si ChromaDB déjà fourni)
```bash
# Scraper le site
python scrape_imt.py
# Indexer les documents
python index.py
```

### 6. Lancer l'application
```bash
chainlit run app.py
```

## 🤖 Fonctionnalités

- **RAG Multi-sources**: Réponses précises basées sur le contenu réel du site imt.sn.
- **Actions Intelligentes**:
  - Remplissage automatique de formulaire de contact.
  - Envoi d'emails formels au directeur.
- **Mémoire & Contexte**: Conservation de l'historique de conversation via Redis.
- **Observabilité**: Tracing complet des appels LLM et des actions via Langfuse.
- **Multimodalité**: Support des messages vocaux (STT/TTS).
- **Génération de PDF**: Recommandations de formation personnalisées en format PDF.

## 👥 Équipe

- **Membre 1**: Scraping, RAG, VectorDB
- **Membre 2**: CrewAI setup, Outils Actions
- **Membre 3**: Chainlit UI, Redis, Langfuse

---
*Projet réalisé dans le cadre de la formation IMT Agent IA.*
