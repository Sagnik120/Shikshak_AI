import json
import logging
from typing import Optional
from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter
from modules.ml_core.src.misconception.taxonomy_loader import TaxonomyLoader

logger = logging.getLogger(__name__)

class MisconceptionClassifier:
    def __init__(self, llm_adapter: LLMAdapter, taxonomy_loader: Optional[TaxonomyLoader] = None):
        self.llm_adapter = llm_adapter
        self.taxonomy_loader = taxonomy_loader or TaxonomyLoader()
        
    def classify(self, raw_answer: str, expected_concept: str, subject: str) -> Optional[str]:
        """Classify an incorrect answer against a known taxonomy."""
        taxonomy = self.taxonomy_loader.load_taxonomy(subject)
        
        if not taxonomy:
            # Fallback when no taxonomy is available for the subject
            logger.info(f"Skipping misconception classification for unsupported subject: {subject}")
            return None
            
        valid_tags = [t["tag"] for t in taxonomy]
        taxonomy_context = json.dumps(taxonomy, indent=2)
        
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an expert educator analyzing an incorrect student answer to identify underlying misconceptions.\n"
                    f"Choose ONLY ONE tag from the following taxonomy for the subject '{subject}':\n"
                    f"{taxonomy_context}\n\n"
                    "Respond with a JSON object containing a single key 'misconception_tag' with the chosen tag string. "
                    "If none of the tags apply, set 'misconception_tag' to null."
                )
            },
            {
                "role": "user", 
                "content": f"Expected Concept: {expected_concept}\nStudent Answer: {raw_answer}"
            }
        ]
        
        try:
            response_str = self.llm_adapter.complete(messages=messages)
            if response_str.startswith("```json"):
                response_str = response_str.strip("`").strip("json").strip()
            
            result_dict = json.loads(response_str)
            tag = result_dict.get("misconception_tag")
            
            if tag and tag not in valid_tags:
                logger.warning(f"LLM returned novel/unclassified misconception tag: '{tag}' for subject '{subject}'.")
                return None
                
            return tag
        except Exception as e:
            logger.error(f"Misconception classification failed: {e}")
            return None
