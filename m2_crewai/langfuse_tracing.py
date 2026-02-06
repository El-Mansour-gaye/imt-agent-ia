"""Langfuse Integration for LLM Tracing"""

import os
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()


class LangfuseTracer:
    """Integrate Langfuse for LLM observability"""
    
    def __init__(self):
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        if self.public_key and self.secret_key:
            self.langfuse = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            print(f"✅ Langfuse connecté: {self.host}")
        else:
            print("⚠️ Langfuse keys manquantes")
            self.langfuse = None

    def start_trace(self, name: str):
        # Utiliser trace() si disponible (v2), sinon constructor simple
        if self.langfuse:
            try:
                self.current_trace = self.langfuse.trace(name=name)
            except AttributeError:
                # Fallback pour versions où trace se crée différemment
                # On simule un objet trace pour éviter les plantages
                class MockTrace:
                    def span(self, **kwargs): return MockSpan()
                class MockSpan:
                    def end(self, **kwargs): pass
                self.current_trace = MockTrace()
            return self.current_trace
        return None

    def start_span(self, name: str, metadata: dict = None):
        if hasattr(self, 'current_trace') and self.current_trace:
            try:
                self.current_span = self.current_trace.span(name=name, metadata=metadata)
                return self.current_span
            except: pass
        return None

    def end_span(self, name: str, metadata: dict = None):
        if hasattr(self, 'current_span') and self.current_span:
            try:
                self.current_span.end(metadata=metadata)
                self.current_span = None
            except: pass

    def end_trace(self, metadata: dict = None):
        if hasattr(self, 'current_trace') and self.current_trace:
            try:
                self.langfuse.flush()
                self.current_trace = None
            except: pass

    def trace_agent_action(self, agent_name: str, action: str, result: str):
        """Trace an agent action"""
        if not self.langfuse: return
        try:
            self.langfuse.trace(
                name=f"agent_action_{agent_name}",
                user_id=agent_name,
                metadata={
                    "action": action,
                    "result": result
                }
            )
        except: pass
    
    def trace_llm_call(self, model: str, prompt: str, completion: str):
        """Trace an LLM API call"""
        if not self.langfuse: return
        try:
            self.langfuse.trace(
                name="llm_call",
                metadata={
                    "model": model,
                    "prompt_length": len(prompt),
                    "completion_length": len(completion)
                }
            )
        except: pass
    
    def flush(self):
        """Flush all traces to Langfuse"""
        if self.langfuse:
            self.langfuse.flush()


# Example usage
def get_tracer():
    """Get a Langfuse tracer instance"""
    return LangfuseTracer()