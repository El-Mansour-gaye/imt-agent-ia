
## Agents CrewAI

### 1. Researcher
- **Rôle**: Expert Recherche IMT Dakar
- **Outils**: `imt_rag_search()` (M1)
- **Responsabilité**: Trouver informations précises
- **Output**: Informations structurées avec sources

### 2. Actioneer  
- **Rôle**: Assistant Actions Automatisées
- **Outils**: 
  - `fill_contact_form()` - Formulaire IMT
  - `send_director_email()` - Email directeur
- **Responsabilité**: Exécuter actions pratiques

### 3. Manager
- **Rôle**: Coordinateur de Processus
- **Outils**: Aucun (raisonnement pur)
- **Responsabilité**: Analyser → Planifier → Déléguer

## Workflow

```python
# Initialisation
crew = IMTCrew(session_id="user_123")

# Exécution
result = crew.kickoff({
    "query": "frais ISI + remplis formulaire",
    "nom": "Jean",
    "email": "jean@ex.com"
})

# Résultat
print(result["response"])  # Réponse complète