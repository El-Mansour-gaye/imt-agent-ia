"""
M2 - Configuration CrewAI avec 3 agents
Intègre RAG (M1) + Actions + Memory + Observability
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from uuid import uuid4

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from dotenv import load_dotenv

# Import des modules M1 (simulés si non disponibles)
try:
    from rag_tools import imt_rag_search
    RAG_AVAILABLE = True
except ImportError:
    print("⚠️ M1 RAG non disponible, mode simulation activé")
    RAG_AVAILABLE = False
    def imt_rag_search(query: str) -> List[Dict]:
        return [{
            "content": f"Simulation RAG pour: {query}",
            "score": 0.95,
            "source": "imt.sn/simulation"
        }]

# Import mémoire Redis avec fallback automatique
try:
    from .crew_memory import RedisMemoryManager, VolatileMemoryManager
    memory_manager = RedisMemoryManager()
    if not getattr(memory_manager, "available", False):
        print("⚠️ Redis non disponible (ping échoué), passage en mode mémoire volatile")
        memory_manager = VolatileMemoryManager()
except (ImportError, Exception) as e:
    print(f"⚠️ Erreur chargement Redis: {e}, mode mémoire volatile")
    memory_manager = VolatileMemoryManager()

# Import tracing Langfuse
try:
    from .langfuse_tracing import LangfuseTracer
    tracer = LangfuseTracer()
except ImportError:
    print("⚠️ Langfuse non disponible, mode tracing simulé")
    tracer = None

# Chargement variables d'environnement
load_dotenv()

# ==================== CONFIGURATION LLM ====================
def get_llm():
    """Configure l'LLM via l'interface native de CrewAI (Grok par défaut si dispo, sinon Gemini)"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    xai_api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

    # Construction de la liste de modèles et fallbacks
    # Priorité à Grok (xAI) comme demandé par l'utilisateur
    if xai_api_key:
        model_name = os.getenv("GROK_MODEL") or os.getenv("XAI_MODEL", "grok-2-latest")
        if model_name.startswith("xai/"):
            model_name = model_name.replace("xai/", "")

        primary = f"xai/{model_name}"

        # Fallbacks
        fallbacks = []
        if gemini_api_key:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            if gemini_model.startswith("gemini/"):
                gemini_model = gemini_model.replace("gemini/", "")
            fallbacks.append(f"gemini/{gemini_model}")

        print(f"🚀 Configuration Grok ({model_name}) - Fallback Gemini: {bool(gemini_api_key)}")
        try:
            return LLM(
                model=primary,
                fallback_models=fallbacks,
                api_key=xai_api_key,
                temperature=0.4,
                max_tokens=2000
            )
        except Exception as e:
            print(f"⚠️ Erreur initialisation Grok: {e}")

    if gemini_api_key:
        # Gemini si Grok non dispo
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        if model_name.startswith("gemini/"):
            model_name = model_name.replace("gemini/", "")

        print(f"🪄 Configuration Gemini ({model_name}) par défaut")
        try:
            return LLM(
                model=f"gemini/{model_name}",
                api_key=gemini_api_key,
                temperature=0.4,
                max_tokens=2000
            )
        except Exception as e:
            print(f"⚠️ Erreur initialisation Gemini: {e}")

    print("❌ Aucune clé API valide trouvée (GEMINI_API_KEY ou XAI_API_KEY)")
    return None

llm = get_llm()

# ==================== OUTILS CREWAI ====================
@tool("Recherche Informations IMT")
def recherche_imt_tool(query: str) -> str:
    """
    Recherche des informations sur l'IMT via RAG.
    Retourne des informations précises avec sources.
    
    Args:
        query: Question de l'utilisateur
        
    Returns:
        str: Informations structurées avec citations
    """
    if tracer:
        tracer.start_span("rag_search", {"query": query})
    
    try:
        results = imt_rag_search(query)
        
        # Formatter la réponse
        formatted = "📚 **Résultats de recherche IMT:**\n\n"
        for i, result in enumerate(results[:3], 1):
            formatted += f"{i}. {result['content']}\n"
            if result.get('source'):
                formatted += f"   Source: {result['source']}\n"
            formatted += "\n"
        
        if tracer:
            tracer.end_span("rag_search", {"results_count": len(results)})
        
        return formatted
    except Exception as e:
        error_msg = f"❌ Erreur recherche: {str(e)}"
        if "429" in str(e) or "quota" in str(e).lower():
            error_msg = "⚠️ Le service de recherche est temporairement saturé (Quota API). Veuillez réessayer dans quelques instants."

        if tracer:
            tracer.end_span("rag_search", {"error": str(e)})
        return error_msg

@tool("Remplir Formulaire Contact IMT")
def formulaire_contact_tool(nom: str, email: str, message: str) -> str:
    """
    Remplit le formulaire de contact sur imt.sn/contact
    
    Args:
        nom: Nom complet
        email: Adresse email
        message: Message à envoyer
        
    Returns:
        str: Statut d'exécution avec preuve
    """
    if tracer:
        tracer.start_span("contact_form", {"nom": nom, "email": email})
    
    try:
        # Utilisation de l'interface unifiée action_tools
        from m2_actions.action_tools import fill_contact_form
        result = fill_contact_form(nom=nom, email=email, message=message)
        
        if tracer:
            tracer.end_span("contact_form", {"success": result.get("status") in ["success", "simulated"]})
        
        return f"✅ Formulaire soumis: {result}"
    except Exception as e:
        error_msg = f"❌ Erreur formulaire: {str(e)}"
        if tracer:
            tracer.end_span("contact_form", {"error": str(e)})
        return error_msg

@tool("Envoyer Email au Directeur IMT")
def email_directeur_tool(sujet: str, corps: str) -> str:
    """
    Envoie un email formel au directeur de l'IMT
    
    Args:
        sujet: Sujet de l'email
        corps: Contenu du message
        
    Returns:
        str: Confirmation d'envoi
    """
    if tracer:
        tracer.start_span("director_email", {"sujet": sujet})
    
    try:
        # Utilisation de l'interface unifiée action_tools
        from m2_actions.action_tools import send_director_email
        result = send_director_email(sujet=sujet, corps=corps)
        
        if tracer:
            tracer.end_span("director_email", {"sent": result.get("status") in ["sent", "success", "simulated"]})
        
        return f"📧 Email envoyé: {result}"
    except Exception as e:
        error_msg = f"❌ Erreur email: {str(e)}"
        if tracer:
            tracer.end_span("director_email", {"error": str(e)})
        return error_msg

# ==================== AGENTS CREWAI ====================
def create_agents(session_id: str = None):
    """Crée les 3 agents CrewAI avec mémoire de session"""
    
    # Charger l'historique de la session
    context_history = ""
    if session_id:
        history = memory_manager.get_session_history(session_id, limit=10)
        if history:
            context_history = "\nContexte précédent:\n" + "\n".join(
                [f"- {h['role']}: {h['content'][:100]}..." for h in history]
            )
    
    # Agent 1: Researcher (RAG)
    researcher = Agent(
        role="Analyste Expert IMT Dakar",
        goal="Fournir des informations précises sur l'IMT et identifier si une action (contact/email) est pertinente.",
        backstory="""Vous êtes l'Analyste Principal de l'IMT Dakar. Votre expertise couvre tous les programmes,
        les frais de scolarité et les processus d'admission. Votre rôle est de fournir des réponses basées
        uniquement sur les faits extraits du RAG. De plus, vous devez détecter si la requête de l'utilisateur
        nécessite une escalade via le formulaire de contact ou un email au directeur. Si une action est nécessaire,
        vous vérifiez scrupuleusement si nous avons déjà le NOM, l'EMAIL et le MESSAGE de l'utilisateur.""",
        tools=[recherche_imt_tool],
        llm=llm,
        verbose=True,
        memory=False,
        max_iter=3
    )
    
    # Agent 2: Actioneer (Actions pratiques)
    actioneer = Agent(
        role="Coordonnateur d'Actions IMT",
        goal="Exécuter les outils d'automatisation uniquement lorsque toutes les données requises sont présentes.",
        backstory="""Vous êtes un expert en exécution technique. Votre rigueur est absolue : vous ne déclenchez
        jamais une action (formulaire ou email) s'il manque une information clé (nom, email ou corps du message).
        Si des informations manquent, vous listez précisément ce qui fait défaut au lieu d'utiliser un outil.
        Votre succès se mesure à la précision de vos rapports d'exécution.""",
        tools=[formulaire_contact_tool, email_directeur_tool],
        llm=llm,
        verbose=True,
        memory=False,
        max_iter=2
    )
    
    # Agent 3: Manager (Coordination & Synthèse)
    manager = Agent(
        role="Directeur de la Relation Étudiant IMT",
        goal="Assurer une expérience utilisateur fluide, chaleureuse et collecter les informations manquantes.",
        backstory="""Vous êtes le visage de l'IMT Dakar. Votre priorité est la satisfaction de l'utilisateur.
        Vous synthétisez le travail de l'Analyste et du Coordonnateur d'Actions. Si une action était prévue mais
        qu'il manquait des informations (nom, email, etc.), vous les demandez avec courtoisie et professionnalisme
        à l'utilisateur. Vos réponses doivent être engageantes et encourager l'interaction.""",
        llm=llm,
        verbose=True,
        memory=False,
        max_iter=2
    )
    
    return researcher, actioneer, manager, context_history

# ==================== CREW PRINCIPAL ====================
class IMTCrew:
    """Crew principal IMT avec mémoire et tracing"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid4())[:8]
        print(f"🆔 Session: {self.session_id}")
        
        # Créer les agents
        self.researcher, self.actioneer, self.manager, self.context = create_agents(self.session_id)
        
        # Créer les tâches
        self.tasks = self._create_tasks()
        
        # Initialiser le crew
        self.crew = Crew(
            agents=[self.researcher, self.actioneer, self.manager],
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
            full_output=False
        )
        
        # Démarrer le trace Langfuse
        if tracer:
            tracer.start_trace(f"imt_session_{self.session_id}")
    
    def _create_tasks(self):
        """Crée les tâches pour les agents avec gestion de collecte d'informations"""
        
        # Tâche 1: Analyse & Recherche
        research_task = Task(
            description="""Analyse approfondie de la requête: '{query}'.
            
            {context}
            
            Instructions:
            1. RECHERCHE: Utilise le RAG pour trouver des réponses précises sur l'IMT.
            2. DIAGNOSTIC: L'utilisateur a-t-il besoin d'une action de contact (formulaire/email) ?
            3. VÉRIFICATION: Si une action est nécessaire, vérifie si nous avons dans le contexte ou la requête:
               - Le Nom complet
               - L'Email
               - Le Message spécifique
            4. SORTIE: Fournis la réponse informative et liste CLAIREMENT les données manquantes pour une éventuelle action.""",
            agent=self.researcher,
            expected_output="Analyse de la requête, informations extraites et inventaire des données utilisateur disponibles.",
            output_file="outputs/research_result.md"
        )
        
        # Tâche 2: Exécution de l'Action (Conditionnelle)
        action_task = Task(
            description="""Décision d'exécution pour la requête: '{query}'.
            
            Instructions:
            1. Analyse l'inventaire des données fourni par le Researcher.
            2. Si une action est requise ET que TOUTES les données (Nom, Email, Message) sont présentes, exécute l'outil approprié.
            3. S'il manque ne serait-ce qu'une information, N'UTILISE AUCUN OUTIL et indique précisément : 'ACTION_INTERROMPUE: Manque [liste des champs]'.
            4. Si aucune action n'est demandée, indique 'STATUT: Information uniquement'.""",
            agent=self.actioneer,
            expected_output="Résultat de l'outil ou rapport d'interruption pour données manquantes.",
            context=[research_task],
            output_file="outputs/execution_report.md"
        )

        # Tâche 3: Interaction Utilisateur & Synthèse
        synthesis_task = Task(
            description="""Synthèse finale et engagement pour la requête: '{query}'.
            
            Instructions:
            1. Si le Coordonnateur a signalé 'ACTION_INTERROMPUE', demande à l'utilisateur les informations manquantes (Nom, Email ou détails du message) de manière très courtoise. Explique pourquoi nous en avons besoin pour l'aider davantage.
            2. Si l'action a réussi, partage la confirmation et les preuves.
            3. Dans tous les cas, fournis une réponse complète et chaleureuse basée sur les recherches de l'Analyste.
            4. Adopte un ton enthousiaste, professionnel et digne d'un représentant de l'IMT Dakar.""",
            agent=self.manager,
            expected_output="Réponse finale chaleureuse, informative, ou demande d'informations complémentaires.",
            context=[research_task, action_task]
        )
        
        return [research_task, action_task, synthesis_task]
    
    def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lance l'exécution du crew avec tracing et mémoire
        
        Args:
            inputs: {"query": "requête utilisateur", ...}
            
        Returns:
            Dict avec résultats complets
        """
        query = inputs.get("query", "")
        
        # Sauvegarder la requête dans l'historique
        memory_manager.save_to_history(
            self.session_id, 
            role="user", 
            content=query
        )
        
# Ajouter le contexte à la requête (toujours fournir une valeur)
        inputs_with_context = inputs.copy()
        inputs_with_context["context"] = self.context if self.context else ""

        
        print(f"🚀 Démarrage CrewAI pour: '{query[:50]}...'")
        
        try:
            # Exécuter le crew
            result = self.crew.kickoff(inputs=inputs_with_context)
            
            # Sauvegarder la réponse
            memory_manager.save_to_history(
                self.session_id,
                role="assistant",
                content=str(result)
            )
            
            # Fin du trace
            if tracer:
                tracer.end_trace({"query": query, "session": self.session_id})
            
            return {
                "success": True,
                "session_id": self.session_id,
                "response": str(result),
                "timestamp": datetime.now().isoformat(),
                "raw_output": result.raw if hasattr(result, 'raw') else result
            }
            
        except Exception as e:
            error_msg = f"❌ Erreur CrewAI: {str(e)}"
            print(error_msg)
            
            if tracer:
                tracer.end_trace({"error": str(e), "query": query})
            
            return {
                "success": False,
                "session_id": self.session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_session_info(self) -> Dict:
        """Récupère les informations de session"""
        history = memory_manager.get_session_history(self.session_id, limit=20)
        return {
            "session_id": self.session_id,
            "history_count": len(history),
            "recent_history": history[-5:] if history else []
        }

# Instance globale pour usage simple
imt_crew_instance = None

def get_imt_crew(session_id: str = None) -> IMTCrew:
    """Factory pour obtenir une instance de crew"""
    global imt_crew_instance
    if imt_crew_instance is None or session_id:
        imt_crew_instance = IMTCrew(session_id)
    return imt_crew_instance

# ==================== USAGE SIMPLE ====================
if __name__ == "__main__":
    # Exemple d'utilisation
    print("🧪 Test CrewAI M2 - Agent IMT")
    print("=" * 60)
    
    # Créer une instance
    crew = get_imt_crew("test_session_001")
    
    # Test 1: Recherche simple
    print("\n1. Test recherche d'information:")
    result1 = crew.kickoff({"query": "Quels sont les frais de la licence ISI ?"})
    print(f"✅ Réponse: {result1['response'][:200]}...")
    
    # Test 2: Avec action
    print("\n2. Test avec action formulaire:")
    result2 = crew.kickoff({
        "query": "Je veux contacter l'IMT pour plus d'informations sur les masters",
        "nom": "Jean Dupont",
        "email": "jean.dupont@example.com",
        "message": "Demande d'info sur les masters en cybersécurité"
    })
    print(f"✅ Résultat: {result2['response'][:200]}...")
    
    print("\n" + "=" * 60)
    print("🎯 M2 CrewAI - PRÊT POUR INTÉGRATION")