"""
Wrapper for the central LLMAdapter from ai_agent_orchestration.
This avoids duplicating the abstract interface across modules.
"""
from modules.ai_agent_orchestration.src.adapters.llm_adapter import LLMAdapter

__all__ = ["LLMAdapter"]
