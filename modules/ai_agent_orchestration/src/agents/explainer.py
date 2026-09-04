import json
from typing import Optional, List, Any
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode, LearnerConstraints
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment

class ExplainerAgent(BaseAgent):
    def generate_segment(
        self,
        node: LessonNode,
        constraints: LearnerConstraints,
        grounding_chunks: Optional[List[Any]] = None,
        previous_feedback: Optional[str] = None
    ) -> TeachingSegment:
        """
        Generate a TeachingSegment from a LessonNode.
        """
        system_prompt = self.load_prompt("explainer_system.md")
        
        user_content = {
            "node": node.model_dump(),
            "constraints": constraints.model_dump()
        }
        
        if grounding_chunks:
            # Enforce anti-hallucination when grounding context is present
            user_content["grounding_context"] = [
                c.text if hasattr(c, "text") else str(c) 
                for c in grounding_chunks
            ]
            
        if previous_feedback:
            # Used for MODIFY transitions
            user_content["previous_feedback"] = previous_feedback
            user_content["instruction"] = "The previous explanation was misunderstood or incomplete. You MUST provide a NEW analogy or example to explain the concept. Do not repeat the previous explanation verbatim."
            
        user_prompt = f"Please generate a teaching segment based on the following inputs:\n{json.dumps(user_content, indent=2)}"
        
        return self.call_llm_json(system_prompt, user_prompt, TeachingSegment, max_retries=2)
