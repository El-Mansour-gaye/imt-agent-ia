# Pipeline de Données IMT Agent IA (M1)

Ce document décrit l'architecture et l'utilisation du pipeline de données pour l'agent LLM de l'IMT.

## Architecture

Le pipeline est divisé en trois composants principaux :

1.  **Scraping (feature/m1-scraping)** : Utilise Scrapy pour crawler `www.imt.sn`, extraire le contenu textuel et les liens, et sauvegarder les données dans `imt_data.json`.
2.  **RAG Core (feature/m1-rag-core)** : Indexation des documents dans ChromaDB. Utilise Gemini (`text-embedding-004`) pour les embeddings et `tiktoken` pour le découpage récursif des textes en chunks de 512 tokens.
3.  **Auto-refresh & Citations (feature/m1-auto-refresh)** : Gestion de la fraîcheur des données via Redis et génération de réponses citées avec Gemini-1.5-pro.

## Utilisation

### 1. Scraping
Pour lancer le crawl complet du site :
```bash
python scrape_imt.py
```
Ceci générera un fichier `imt_data.json` contenant les pages extraites.

### 2. Indexation (RAG)
Pour indexer les données dans la base vectorielle ChromaDB :
```bash
# Pour une première indexation ou mise à jour
python index.py

# Pour reconstruire entièrement la base
python index.py --rebuild
```

### 3. Recherche RAG simple
```python
from rag_tools import imt_rag_search
results = imt_rag_search("frais de scolarité ISI")
print(results)
```

### 4. Auto-refresh
Vérifie si les données datent de plus de 7 jours et relance le scraping/indexation si nécessaire :
```python
from refresh_tool import refresh_data_if_stale
refresh_data_if_stale(days=7)
```

### 5. Recherche augmentée avec citations
Génère une réponse complète en utilisant Gemini et les sources du RAG :
```python
from refresh_tool import imt_enhanced_search
response = imt_enhanced_search("Quels sont les frais pour la licence ISI ?")
print(response['answer'])
print(response['sources'])
```

## Configuration (.env)
Assurez-vous d'avoir les variables suivantes dans votre fichier `.env` :
- `GEMINI_API_KEY` : Votre clé API Google Gemini.
- `REDIS_URL` : URL de votre instance Redis (ex: `redis://localhost:6379`).
- `CHROMA_PATH` : Chemin pour la persistance de ChromaDB (ex: `./chroma_db`).
