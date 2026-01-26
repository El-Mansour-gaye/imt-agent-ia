Projet IMT Agent IA - Équipe Mansour GAYE, Moustapha DIOP, Chrys YABI

# IMT Agent IA
Agent LLM pour site IMT.sn (Scraping RAG + actions form/email).

## Setup
1. `git clone https://github.com/.../imt-agent-ia`
2. `cp .env.example .env` → ajoutez GEMINI_API_KEY etc.
3. `docker-compose up -d` (Redis)
4. `pip install -r requirements.txt`
5. `chainlit run app.py`

## Workflow Git (OBLIGATOIRE)
- Travail sur **feature/m1-scraping** etc. (votre nom).
- Commits: "M1: Add Scrapy spider".
- PR vers **develop** (review + merge).
- **NE JAMMAIS** push direct main/develop.
- Pull develop souvent !

Branches: main=final, develop=dev.
