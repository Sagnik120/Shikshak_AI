import logging
from typing import List, Optional
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ml_core.src.schemas.evaluation import EvaluationResult

from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter
from modules.ml_core.src.concept_extraction.extractor import extract_concepts as ce_extract
from modules.ml_core.src.answer_evaluation.evaluator import AnswerEvaluator
from modules.ml_core.src.misconception.classifier import MisconceptionClassifier
from modules.ml_core.src.visual_suggestion.suggester import VisualTypeSuggester

logger = logging.getLogger(__name__)

class MLCoreService:
    """Facade for ML Core providing evaluation, concept extraction, and visual suggestion."""
    
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None):
        # Allow injecting an LLMAdapter; otherwise we don't have one and will crash if needed.
        self.llm_adapter = llm_adapter
        if self.llm_adapter:
            self.evaluator = AnswerEvaluator(self.llm_adapter)
            self.misconception_classifier = MisconceptionClassifier(self.llm_adapter)
            self.visual_suggester = VisualTypeSuggester(self.llm_adapter)
        else:
            self.evaluator = None
            self.misconception_classifier = None
            self.visual_suggester = None
            logger.warning("MLCoreService initialized without LLMAdapter. Some functions will fail.")

    def evaluate_answer(
        self, 
        response: StudentResponse, 
        expected_concept: str = "", 
        grounding_text: Optional[str] = None,
        subject: str = "physics" # Add subject for misconception taxonomy
    ) -> EvaluationResult:
        """Evaluate a student response against an expected concept."""
        if not self.evaluator:
            raise ValueError("AnswerEvaluator requires LLMAdapter to be configured.")
            
        result = self.evaluator.evaluate(response, expected_concept, grounding_text)
        
        # If incorrect, try to classify misconception
        if not result.correct and self.misconception_classifier:
            tag = self.misconception_classifier.classify(response.raw_answer, expected_concept, subject)
            if tag:
                result.misconception_tag = tag
                # Optionally augment feedback if tag found
                result.feedback_text += f" (Note: identified possible misconception '{tag}')"
                
        return result
        
    def extract_concepts(self, chunk_texts: List[str]) -> List[str]:
        """Extract key concepts from parsed text chunks."""
        return ce_extract(chunk_texts)
        
    def suggest_visual_type(self, subject: str, concept: str) -> str:
        """Suggest a visual type for a given subject and concept."""
        if not self.visual_suggester:
            raise ValueError("VisualTypeSuggester requires LLMAdapter to be configured.")
        return self.visual_suggester.suggest(subject, concept)
