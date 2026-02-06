"""
M2 - Configuration CrewAI avec 3 agents
Intègre RAG (M1) + Actions + Memory + Observability
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from uuid import uuid4

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
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

# Import mémoire Redis
try:
    from .crew_memory import RedisMemoryManager
    memory_manager = RedisMemoryManager()
except ImportError:
    print("⚠️ Redis non disponible, mode mémoire volatile")
    from .crew_memory import VolatileMemoryManager
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
    """Configure Gemini 1.5-pro avec fallback"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("⚠️ GEMINI_API_KEY manquante, mode simulation")
        
        class MockLLM:
            def generate_response(self, prompt):
                return f"[SIMULATION] Réponse à: {prompt[:50]}..."
        
        return MockLLM()
    
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=2000,
            convert_system_message_to_human=True
        )
    except Exception as e:
        print(f"❌ Erreur Gemini: {e}, mode simulation")
        
        class FallbackLLM:
            def generate_response(self, prompt):
                return f"[FALLBACK] Question: {prompt[:100]}..."
        
        return FallbackLLM()

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
        # Import dynamique pour éviter dépendance circulaire
        from m2_actions.playwright_form import fill_imt_contact_form
        result = fill_imt_contact_form(nom, email, message)
        
        if tracer:
            tracer.end_span("contact_form", {"success": result.get("status") == "success"})
        
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
        from m2_actions.email_sender import send_director_email
        result = send_director_email(sujet, corps)
        
        if tracer:
            tracer.end_span("director_email", {"sent": result.get("status") == "sent"})
        
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
        role="Expert Recherche IMT Dakar",
        goal="Trouver des informations précises et vérifiées sur les formations, frais, procédures de l'IMT",
        backstory="""Spécialiste de l'IMT avec 10 ans d'expérience, accès à toutes les bases de données
        de l'institut. Méticuleux, précis, et toujours à jour sur les informations officielles.""",
        tools=[recherche_imt_tool],
        llm=llm,
        verbose=True,
        memory=False,
        max_iter=3
    )
    
    # Agent 2: Actioneer (Actions pratiques)
    actioneer = Agent(
        role="Assistant Actions Automatisées IMT",
        goal="Exécuter des actions pratiques comme remplir des formulaires, envoyer des emails, et traiter les demandes",
        backstory="""Assistant technique expert en automatisation, maîtrise parfaite des outils web
        et des protocoles de communication. Pragmatique et efficace.""",
        tools=[formulaire_contact_tool, email_directeur_tool],
        llm=llm,
        verbose=True,
        memory=False,
        max_iter=2
    )
    
    # Agent 3: Manager (Coordination)
    manager = Agent(
        role="Manager de Processus IMT",
        goal="Coordonner les agents pour fournir une réponse complète et exécuter les actions demandées",
        backstory="""Manager expérimenté en gestion de projets éducatifs. Excellente capacité d'analyse
        et de planification. S'assure que toutes les demandes sont traitées de manière optimale.""",
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
            full_output=True
        )
        
        # Démarrer le trace Langfuse
        if tracer:
            tracer.start_trace(f"imt_session_{self.session_id}")
    
    def _create_tasks(self):
        """Crée les tâches pour les agents"""
        
        # Tâche 1: Recherche (Researcher)
        research_task = Task(
            description="""Analyse la requête utilisateur et recherche des informations précises.
            
            Requête: {query}
            
            {context}
            
            Instructions:
            1. Identifie le type d'information demandée (frais, inscriptions, contacts, formations)
            2. Utilise l'outil de recherche RAG pour obtenir des informations fiables
            3. Structure la réponse de manière claire avec sources
            4. Identifie si une action est nécessaire (formulaire, email)
            
            Format de sortie:
            - Titre de la section
            - Informations principales
            - Sources/citations
            - Actions recommandées (si applicable)""",
            agent=self.researcher,
            expected_output="Informations structurées avec sources et recommandations d'action",
            output_file="outputs/research_result.md"
        )
        
        # Tâche 2: Planification (Manager)
        planning_task = Task(
            description="""Analyse les résultats de recherche et planifie les actions nécessaires.
            
            
            
            Instructions:
            1. Évalue si une action est requise (formulaire de contact, email au directeur)
            2. Si action requise, détermine le type d'action et les données nécessaires
            3. Prépare un plan d'exécution clair
            4. Transmet les instructions à l'Actioneer
            
            Format de sortie:
            - Évaluation de la demande
            - Plan d'action (si applicable)
            - Instructions pour l'Actioneer""",
            agent=self.manager,
            expected_output="Plan d'action avec instructions détaillées",
            context=[research_task],
            output_file="outputs/action_plan.md"
        )
        
        # Tâche 3: Exécution (Actioneer)
        action_task = Task(
            description="""Exécute les actions planifiées par le Manager.
            
            
            
            Instructions:
            1. Suis exactement les instructions du Manager
            2. Utilise les outils appropriés (formulaire, email)
            3. Fournis une confirmation d'exécution avec preuves
            4. Signale toute erreur ou difficulté
            
            Format de sortie:
            - Confirmation d'exécution
            - Résultats/Preuves
            - Statut final""",
            agent=self.actioneer,
            expected_output="Rapport d'exécution avec confirmations",
            context=[planning_task],
            output_file="outputs/execution_report.md"
        )
        
        return [research_task, planning_task, action_task]
    
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