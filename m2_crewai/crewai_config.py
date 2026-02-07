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

# Intégration Multilingue
from m2_bonus.multilingual import detect_lang_and_translate

# Import logger centralisé
try:
    from logger import log_info, log_warn, log_error, log_important
except ImportError:
    def log_info(m): pass
    def log_warn(m): print(m)
    def log_error(m): print(m)
    def log_important(m): print(m)

# Import des modules M1 (simulés si non disponibles)
try:
    from rag_tools import imt_rag_search
    RAG_AVAILABLE = True
except ImportError:
    log_warn("⚠️ M1 RAG non disponible, mode simulation activé")
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
        log_warn("⚠️ Redis non disponible (ping échoué), passage en mode mémoire volatile")
        memory_manager = VolatileMemoryManager()
except (ImportError, Exception) as e:
    log_error(f"⚠️ Erreur chargement Redis: {e}, mode mémoire volatile")
    memory_manager = VolatileMemoryManager()

# Import tracing Langfuse
try:
    from .langfuse_tracing import LangfuseTracer
    tracer = LangfuseTracer()
except ImportError:
    log_warn("⚠️ Langfuse non disponible, mode tracing simulé")
    tracer = None

# Chargement variables d'environnement
load_dotenv()

CREWAI_VERBOSE = os.getenv("CREWAI_VERBOSE", "false").lower() == "true"

# ==================== CONFIGURATION LLM ====================
def get_llm():
    """Configure l'LLM via l'interface native de CrewAI (Groq > Gemini > Grok)"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    xai_api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")

    # Nettoyage des clés
    if groq_api_key: groq_api_key = groq_api_key.strip().lstrip('=')
    if gemini_api_key: gemini_api_key = gemini_api_key.strip().lstrip('=')
    if xai_api_key: xai_api_key = xai_api_key.strip().lstrip('=')

    # Priorité 1: GROQ
    if groq_api_key:
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        log_info(f"🚀 Configuration GROQ ({model_name})")

        # Fallbacks (Utilisation du paramètre 'fallbacks' pour LiteLLM via CrewAI)
        fallbacks = []
        if gemini_api_key: fallbacks.append(f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-2.0-flash').replace('gemini/', '')}")
        if xai_api_key: fallbacks.append(f"xai/{os.getenv('GROK_MODEL', 'grok-2-latest').replace('xai/', '')}")

        try:
            return LLM(
                model=f"groq/{model_name.replace('groq/', '')}",
                fallbacks=fallbacks,
                api_key=groq_api_key,
                temperature=0.4,
                max_tokens=2000
            )
        except Exception as e:
            log_error(f"⚠️ Erreur initialisation GROQ: {e}")

    # Priorité 2: Gemini
    if gemini_api_key:
        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        if model_name.startswith("gemini/"):
            model_name = model_name.replace("gemini/", "")

        log_info(f"🪄 Configuration Gemini ({model_name})")

        fallbacks = []
        if groq_api_key: fallbacks.append(f"groq/{os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').replace('groq/', '')}")
        if xai_api_key: fallbacks.append(f"xai/{os.getenv('GROK_MODEL', 'grok-2-latest').replace('xai/', '')}")

        try:
            return LLM(
                model=f"gemini/{model_name}",
                fallbacks=fallbacks,
                api_key=gemini_api_key,
                temperature=0.4,
                max_tokens=2000
            )
        except Exception as e:
            log_error(f"⚠️ Erreur initialisation Gemini: {e}")

    log_error("❌ Aucune clé API valide trouvée (GEMINI_API_KEY ou XAI_API_KEY)")
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
    # Prompt de secours (matches Langfuse 'imt_expert_system')
    default_backstory = """Tu es l'assistant IA exclusif de l'IMT Dakar.

    RÈGLE DE SÉCURITÉ ABSOLUE :
    - Ton périmètre de connaissance est STRICTEMENT limité à l'IMT (Institut Mines-Télécom), ses formations (Bachelor, etc.), ses locaux à Dakar, et ses partenaires.
    - Si l'utilisateur pose une question hors sujet (ex: météo, cuisine, politique, sport, ou une autre école sans lien avec l'IMT), réponds systématiquement :
      "Désolé, en tant qu'assistant dédié à l'IMT Dakar, je ne peux répondre qu'aux questions concernant notre institut et ses formations."

    CONSIGNES DE RÉPONSE :
    1. Analyse la requête pour voir si elle concerne l'IMT.
    2. Utilise les outils (RAG) pour chercher l'information sur imt.sn.
    3. Si l'information n'est pas dans ta base de connaissances IMT, indique que tu n'as pas l'information spécifique mais reste dans le cadre de l'école.
    4. Applique les règles de concision (2 phrases max) et cite "Source : imt.sn"."""

    # Récupération du prompt depuis Langfuse (Priorité)
    researcher_backstory = default_backstory
    callbacks = []
    if tracer:
        researcher_backstory = tracer.get_prompt("imt_expert_system", fallback=default_backstory)
        handler = tracer.get_callback_handler()
        if handler:
            callbacks.append(handler)

    researcher = Agent(
        role="Expert IMT Dakar",
        goal="Informer exclusivement sur l'IMT Dakar et identifier les infos de profil.",
        backstory=researcher_backstory,
        tools=[recherche_imt_tool],
        llm=llm,
        verbose=CREWAI_VERBOSE,
        memory=False,
        max_iter=3,
        callbacks=callbacks
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
        verbose=CREWAI_VERBOSE,
        memory=False,
        max_iter=2
    )
    
    # Agent 3: Manager (Coordination & Synthèse)
    manager = Agent(
        role="Chatbot Assistant de l'IMT Dakar",
        goal="Fournir des réponses d'élite, ultra-concises en tant qu'assistant virtuel de l'IMT.",
        backstory="""Vous êtes le chatbot assistant officiel de l'IMT Dakar. Votre ton est 'Elite & Direct'.

        RÈGLES DE FER :
        1. IDENTITÉ : Présentez-vous toujours comme le chatbot assistant de l'IMT Dakar si on vous demande qui vous êtes.
        2. LA RÈGLE DES 2 PHRASES : Si la réponse peut tenir en deux phrases, INTERDICTION d'en faire une troisième.
        3. PAS DE REDIRECTION : INTERDICTION de dire 'visitez notre site' ou 'allez sur imt.sn'. L'utilisateur y est déjà.
        4. DÉCLENCHEMENT OUTILS : Si msg >= 3, dites : 'Vous pouvez contacter le directeur/remplir le formulaire vous-même sur le site ou je peux m'en charger pour vous ici.'
        5. COLLECTE DE DONNÉES : Ne demandez AUCUNE info (Nom/Email) avant que l'utilisateur n'ait dit 'Oui' ou 'Je veux bien' à votre proposition d'aide.
        6. MULTILINGUE : Vous devez impérativement répondre dans la langue détectée de l'utilisateur (Français, Anglais ou Wolof).

        EXEMPLES DE RÉPONSES (FEW-SHOT) :
        - FR : 'Où est l'école ?' -> 'L'IMT Dakar est situé au Point E. C’est le premier groupe public d’écoles d’ingénieurs français au Sénégal.'
        - EN : 'Where is the school?' -> 'IMT Dakar is located at Point E. It is the first public group of French engineering schools in Senegal.'
        - WO : 'Fañ la école bi nekk?' -> 'IMT Dakar mi ngi nekk ci Point E. Mooy goornemant bu jëkk bu ay ekoolu injénieru fofou ca France nekk fii ci Sénégal.'
        - Utilisateur (si msg >= 3) : 'Quels sont les frais ?' -> 'Les frais varient selon le cursus, comptez environ X FCFA par an. Vous pouvez contacter le directeur vous-même sur le site ou je peux m'en charger ici pour vous.'
        - Utilisateur (avec intention) : 'Ok, fais-le pour moi.' -> 'C'est entendu. Pour procéder, j'ai besoin de votre nom, votre email et votre message.'""",
        llm=llm,
        verbose=CREWAI_VERBOSE,
        memory=False,
        max_iter=2
    )
    
    return researcher, actioneer, manager, context_history

# ==================== CREW PRINCIPAL ====================
class IMTCrew:
    """Crew principal IMT avec mémoire et tracing"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid4())[:8]
        log_info(f"🆔 Session: {self.session_id}")
        
        # Créer les agents
        self.researcher, self.actioneer, self.manager, self.context = create_agents(self.session_id)
        
        # Créer les tâches
        self.tasks = self._create_tasks()
        
        # Initialiser le crew
        self.crew = Crew(
            agents=[self.researcher, self.actioneer, self.manager],
            tasks=self.tasks,
            process=Process.sequential,
            verbose=CREWAI_VERBOSE,
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
            description="""Analyse de la requête: '{query}'.
            
            {context}
            
            Instructions:
            1. RECHERCHE: Utilise le RAG pour les questions sur l'IMT. Si la requête contient des infos personnelles (nom, email, etc.), identifie-les.
            2. DIAGNOSTIC: Détermine si l'utilisateur veut effectuer une action de contact (formulaire ou email).
            3. VÉRIFICATION: Liste ce qui est présent et ce qui manque parmi : Nom, Email, Message.""",
            agent=self.researcher,
            expected_output="Informations extraites du RAG et diagnostic sur le besoin d'action de contact.",
            output_file="outputs/research_result.md"
        )
        
        # Tâche 2: Exécution de l'Action (Conditionnelle)
        action_task = Task(
            description="""Décision d'exécution pour: '{query}'.
            
            Instructions:
            1. Si une action de contact est demandée ET que TOUTES les données (Nom, Email, Message) sont présentes, exécute l'outil.
            2. Sinon, ne fais rien et indique simplement si des informations manquent pour un futur contact.
            3. NE BLOQUE PAS la fourniture d'informations générales.""",
            agent=self.actioneer,
            expected_output="Résultat de l'action ou statut des données de contact.",
            context=[research_task],
            output_file="outputs/execution_report.md"
        )

        # Tâche 3: Interaction Utilisateur & Synthèse
        synthesis_task = Task(
            description="""Synthèse finale pour: '{original_query}'.

            LANGUE DE RÉPONSE OBLIGATOIRE : {detected_lang_name}
            (Vous DEVEZ répondre impérativement en {detected_lang_name}).
            
            COMPTEUR DE MESSAGES : {user_messages_count}

            RÈGLES D'OR :
            1. CONCISION : Répondez strictement en 2 PHRASES MAXIMUM (80% des cas). Utilisez des puces si la réponse exige plus de détails.
            2. ZÉRO REDIRECTION : Ne suggérez jamais d'aller sur le site imt.sn.
            3. ANNONCE OUTILS : Si {user_messages_count} >= 3, proposez l'aide de l'IA (Email/Formulaire) en précisant que l'utilisateur peut aussi le faire seul sur le site.
            4. COLLECTE DATA : Demandez les infos (Nom, Email, Message) uniquement APRÈS une confirmation d'intention claire.
            5. FEEDBACK ACTION : Si une action a été exécutée, listez les données transmises et confirmez le succès ou l'échec.""",
            agent=self.manager,
            expected_output="Réponse informative ultra-concise, avec feedback d'action ou proposition d'outil si pertinent.",
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

        # --- DÉTECTION ET TRADUCTION DE LANGUE ---
        lang_res = detect_lang_and_translate(query)
        detected_lang = lang_res.get('detected_language', 'fr')
        detected_lang_name = lang_res.get('detected_language_name', 'français')
        query_translated = lang_res.get('translated_text', query)
        is_translated = lang_res.get('is_translated', False)

        if is_translated:
            log_info(f"🌐 Langue détectée: {detected_lang_name} ({detected_lang}). Traduction interne utilisée.")
        else:
            log_info(f"🌐 Langue détectée: {detected_lang_name} ({detected_lang})")
        # ----------------------------------------
        
        # Sauvegarder la requête dans l'historique
        memory_manager.save_to_history(
            self.session_id, 
            role="user", 
            content=query
        )

        # Récupérer l'historique pour compter les messages utilisateur
        history = memory_manager.get_session_history(self.session_id, limit=100)
        user_messages_count = sum(1 for msg in history if msg['role'] == 'user')
        
        # Ajouter le contexte à la requête (toujours fournir une valeur)
        inputs_with_context = inputs.copy()

        # Utiliser la version traduite pour la recherche et les actions
        inputs_with_context["query"] = query_translated
        inputs_with_context["original_query"] = query
        inputs_with_context["detected_lang_name"] = detected_lang_name

        inputs_with_context["context"] = self.context if self.context else ""
        inputs_with_context["user_messages_count"] = user_messages_count
        
        # Sécurité pour les variables template (ex: Langfuse prompt contenant {extracted_data})
        if "extracted_data" not in inputs_with_context:
            inputs_with_context["extracted_data"] = ""

        log_important(f"🚀 Démarrage CrewAI (Msg #{user_messages_count}) pour: '{query[:50]}...'")
        
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
            log_error(error_msg)
            
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