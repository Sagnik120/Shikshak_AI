from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    """
    Abstract interface for LLM completions (Contract §14).
    Every module using an external AI service MUST go through this interface.
    """
    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Execute an LLM completion.
        
        Args:
            messages: List of message dictionaries.
            tools: Optional list of tool definitions.
            
        Returns:
            The completion response string.
        """
        pass
