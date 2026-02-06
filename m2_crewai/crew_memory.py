"""
M2 - Crew Memory Management
Gestion de la mémoire avec Redis (M3) ou fallback volatile
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


class MemoryManager(ABC):
    """Interface abstraite pour gestionnaires de mémoire"""
    
    @abstractmethod
    def store(self, key: str, value: Any, ttl: int = None) -> bool:
        """Stocker une valeur"""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Any:
        """Récupérer une valeur"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Supprimer une valeur"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Vider la mémoire"""
        pass


class VolatileMemoryManager(MemoryManager):
    """Mémoire volatile (en RAM, sans persistance)"""
    
    def __init__(self):
        self.memory: Dict[str, Dict[str, Any]] = {}
        print("✅ Mémoire volatile initialisée")
    
    def store(self, key: str, value: Any, ttl: int = None) -> bool:
        """Stocker une valeur en RAM"""
        try:
            self.memory[key] = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "ttl": ttl,
                "expires_at": (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None
            }
            return True
        except Exception as e:
            print(f"❌ Erreur stockage mémoire: {e}")
            return False
    
    def retrieve(self, key: str) -> Any:
        """Récupérer une valeur"""
        if key not in self.memory:
            return None
        
        entry = self.memory[key]
        
        # Vérifier l'expiration
        if entry.get("expires_at"):
            if datetime.fromisoformat(entry["expires_at"]) < datetime.now():
                del self.memory[key]
                return None
        
        return entry["value"]
    
    def delete(self, key: str) -> bool:
        """Supprimer une clé"""
        if key in self.memory:
            del self.memory[key]
            return True
        return False
    
    def clear(self) -> bool:
        """Vider la mémoire"""
        self.memory.clear()
        return True

    def save_to_history(self, session_id: str, role: str, content: str):
        """Simulation d'historique en mémoire volatile"""
        key = f"history:{session_id}"
        if key not in self.memory:
            self.memory[key] = {"value": []}
        self.memory[key]["value"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Récupération de l'historique simulé"""
        key = f"history:{session_id}"
        if key not in self.memory:
            return []
        return self.memory[key]["value"][-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques de mémoire"""
        return {
            "total_keys": len(self.memory),
            "memory_type": "volatile",
            "persistent": False
        }


class RedisMemoryManager(MemoryManager):
    """Gestionnaire de mémoire avec Redis (intégration M3)"""
    
    def __init__(self):
        try:
            from redis_manager import redis_client
            self.redis_client = redis_client
            
            # Test de connexion
            self.redis_client.ping()
            print(f"✅ Redis (M3) connecté")
            self.available = True
            
        except ImportError:
            print("⚠️ redis_manager non disponible, fallback mémoire volatile")
            self.available = False
        except Exception as e:
            print(f"⚠️ Connexion Redis échouée ({e}), fallback mémoire volatile")
            self.available = False

    def save_to_history(self, session_id: str, role: str, content: str):
        """Sauvegarde un message dans l'historique (compatible redis_manager)"""
        if not self.available:
            return
        from redis_manager import save_message
        save_message(session_id, role, content)

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Récupère l'historique de session (compatible redis_manager)"""
        if not self.available:
            return []
        from redis_manager import get_last_messages
        return get_last_messages(session_id, limit)
    
    def store(self, key: str, value: Any, ttl: int = None) -> bool:
        """Stocker une valeur dans Redis"""
        if not self.available:
            return False
        
        try:
            # Sérialiser la valeur
            json_value = json.dumps({
                "value": value,
                "created_at": datetime.now().isoformat()
            })
            
            # Stocker avec TTL optionnel
            if ttl:
                self.redis_client.setex(key, ttl, json_value)
            else:
                self.redis_client.set(key, json_value)
            
            return True
        except Exception as e:
            print(f"❌ Erreur Redis set: {e}")
            return False
    
    def retrieve(self, key: str) -> Any:
        """Récupérer une valeur de Redis"""
        if not self.available:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                data = json.loads(value)
                return data.get("value")
            return None
        except Exception as e:
            print(f"❌ Erreur Redis get: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Supprimer une clé"""
        if not self.available:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Erreur Redis delete: {e}")
            return False
    
    def clear(self) -> bool:
        """Vider la base de données"""
        if not self.available:
            return False
        
        try:
            self.redis_client.flushdb()
            return True
        except Exception as e:
            print(f"❌ Erreur Redis flush: {e}")
            return False
    
    def increment_counter(self, key: str, increment: int = 1) -> int:
        """Incrémenter un compteur (pour rate-limiting)"""
        if not self.available:
            return 0
        
        try:
            return self.redis_client.incr(key, increment)
        except Exception as e:
            print(f"❌ Erreur Redis incr: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques Redis"""
        if not self.available:
            return {"status": "unavailable"}
        
        try:
            info = self.redis_client.info()
            return {
                "memory_type": "redis",
                "persistent": True,
                "used_memory": info.get("used_memory_human"),
                "total_keys": self.redis_client.dbsize(),
                "version": info.get("redis_version")
            }
        except Exception as e:
            return {"error": str(e)}


class CrewMemoryContext:
    """Contexte de mémoire pour les agents Crew"""
    
    def __init__(self, manager: MemoryManager = None):
        self.manager = manager or VolatileMemoryManager()
        self.session_id = self._generate_session_id()
        self.conversations: List[Dict[str, Any]] = []
        self.tasks_history: List[Dict[str, Any]] = []
        
    def _generate_session_id(self) -> str:
        """Générer un ID de session unique"""
        import uuid
        return str(uuid.uuid4())
    
    def add_conversation(self, agent: str, role: str, message: str, response: str):
        """Ajouter une entrée de conversation"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "role": role,
            "message": message,
            "response": response
        }
        self.conversations.append(entry)
        
        # Stocker dans le gestionnaire
        key = f"conv:{self.session_id}:{len(self.conversations)}"
        self.manager.store(key, entry, ttl=86400)  # 24h TTL
    
    def add_task_history(self, task_name: str, status: str, result: str, duration: float):
        """Ajouter à l'historique des tâches"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_name": task_name,
            "status": status,
            "result": result,
            "duration_seconds": duration
        }
        self.tasks_history.append(entry)
        
        # Stocker dans le gestionnaire
        key = f"task:{self.session_id}:{task_name}:{len(self.tasks_history)}"
        self.manager.store(key, entry, ttl=604800)  # 7 days TTL
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Obtenir un résumé du contexte"""
        return {
            "session_id": self.session_id,
            "conversations_count": len(self.conversations),
            "tasks_count": len(self.tasks_history),
            "last_conversation": self.conversations[-1] if self.conversations else None,
            "manager_type": type(self.manager).__name__
        }
    
    def export_to_json(self, filepath: str) -> bool:
        """Exporter la mémoire en JSON"""
        try:
            data = {
                "session_id": self.session_id,
                "exported_at": datetime.now().isoformat(),
                "conversations": self.conversations,
                "tasks_history": self.tasks_history
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Mémoire exportée: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Erreur export mémoire: {e}")
            return False
    
    def clear(self) -> bool:
        """Effacer toute la mémoire"""
        self.conversations.clear()
        self.tasks_history.clear()
        return self.manager.clear()


# Legacy compatibility
class CrewMemory:
    """Backward compatibility"""
    
    def __init__(self):
        self.context = CrewMemoryContext()
        self.memory = {
            "conversations": [],
            "tasks_completed": [],
            "context": {}
        }
    
    def add_conversation(self, agent_name: str, message: str):
        """Add a conversation entry to memory"""
        self.memory["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "message": message
        })
    
    def add_task_completion(self, task_name: str, result: str):
        """Record a completed task"""
        self.memory["tasks_completed"].append({
            "timestamp": datetime.now().isoformat(),
            "task": task_name,
            "result": result
        })
    
    def update_context(self, key: str, value: Any):
        """Update context information"""
        self.memory["context"][key] = value
    
    def get_context(self, key: str = None):
        """Retrieve context information"""
        if key:
            return self.memory["context"].get(key)
        return self.memory["context"]
    
    def export_memory(self, filepath: str):
        """Export memory to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.memory, f, indent=2)

