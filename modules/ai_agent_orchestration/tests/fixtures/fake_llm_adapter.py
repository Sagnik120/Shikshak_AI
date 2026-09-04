from typing import List, Dict, Any, Optional
from modules.ai_agent_orchestration.src.adapters.llm_adapter import LLMAdapter

class FakeLLMAdapter(LLMAdapter):
    """
    Deterministic stub for LLMAdapter that returns canned JSON payloads.
    Allows configuring a sequence of responses to simulate retries/repairs.
    """
    def __init__(self, responses: Optional[List[str]] = None):
        # A list of strings to return on sequential calls. Pops from index 0.
        self.responses = responses or []
        self.calls = []

    def complete(self, messages: List[Dict[str, str]]) -> str:
        self.calls.append(messages)
        if not self.responses:
            raise RuntimeError("FakeLLMAdapter ran out of canned responses.")
        return self.responses.pop(0)

    def set_responses(self, responses: List[str]):
        self.responses = responses
        self.calls = []
