import json
import logging
from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter
from modules.ml_core.src.visual_suggestion.rules import get_rule_based_visual

logger = logging.getLogger(__name__)

class VisualTypeSuggester:
    VALID_TYPES = ["equation", "graph", "diagram", "code", "image", "timeline", "map", "simulation"]
    
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter
        
    def suggest(self, subject: str, concept: str) -> str:
        """Suggest visual type using rules first, LLM fallback if ambiguous."""
        
        # 1. Deterministic Rule Table
        rule_match = get_rule_based_visual(subject, concept)
        if rule_match:
            logger.info(f"Visual type '{rule_match}' selected by rule for '{subject}:{concept}'.")
            return rule_match
            
        # 2. LLM Fallback for ambiguous inputs
        logger.info(f"Ambiguous visual type for '{subject}:{concept}'. Using LLM fallback.")
        messages = [
            {
                "role": "system",
                "content": (
                    "You must select the most appropriate visual representation type for a teaching segment.\n"
                    f"Choose EXACTLY ONE of the following: {self.VALID_TYPES}\n"
                    "Respond ONLY with a JSON object: {\"visual_type\": \"<type>\"}."
                )
            },
            {
                "role": "user",
                "content": f"Subject: {subject}\nConcept: {concept}"
            }
        ]
        
        try:
            response_str = self.llm_adapter.complete(messages=messages)
            if response_str.startswith("```json"):
                response_str = response_str.strip("`").strip("json").strip()
            
            result_dict = json.loads(response_str)
            v_type = result_dict.get("visual_type", "").lower()
            
            if v_type in self.VALID_TYPES:
                return v_type
                
            logger.warning(f"LLM returned invalid visual_type '{v_type}'. Falling back to 'image'.")
        except Exception as e:
            logger.error(f"Visual type LLM fallback failed: {e}. Falling back to 'image'.")
            
        return "image"
