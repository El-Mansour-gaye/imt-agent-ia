"""Langfuse Integration for LLM Tracing"""

import os
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()


class LangfuseTracing:
    """Integrate Langfuse for LLM observability"""
    
    def __init__(self):
        self.langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        )
    
    def trace_agent_action(self, agent_name: str, action: str, result: str):
        """Trace an agent action"""
        self.langfuse.trace(
            name=f"agent_action_{agent_name}",
            user_id=agent_name,
            metadata={
                "action": action,
                "result": result
            }
        )
    
    def trace_llm_call(self, model: str, prompt: str, completion: str):
        """Trace an LLM API call"""
        self.langfuse.trace(
            name="llm_call",
            metadata={
                "model": model,
                "prompt_length": len(prompt),
                "completion_length": len(completion)
            }
        )
    
    def flush(self):
        """Flush all traces to Langfuse"""
        self.langfuse.flush()


# Example usage
def get_tracer():
    """Get a Langfuse tracer instance"""
    return LangfuseTracing()
