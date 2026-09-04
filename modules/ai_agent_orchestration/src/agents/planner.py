import json
from typing import Optional, Any
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonPlan, LearnerConstraints

class PlannerAgent(BaseAgent):
    def plan_lesson(
        self,
        constraints: LearnerConstraints,
        source_type: str,
        topic: Optional[str] = None,
        parsed_doc: Optional[Any] = None,
        learner_profile: Optional[Any] = None
    ) -> LessonPlan:
        """
        Generate a LessonPlan from a topic or ParsedDocument.
        """
        system_prompt = self.load_prompt("planner_system.md")
        
        user_content = {
            "source_type": source_type,
            "constraints": constraints.model_dump()
        }
        
        if topic:
            user_content["topic"] = topic
            
        if parsed_doc:
            user_content["document_structure"] = getattr(parsed_doc, "detected_structure", "Document provided")
            
        if learner_profile:
            user_content["learner_profile"] = learner_profile.model_dump() if hasattr(learner_profile, "model_dump") else learner_profile
            
        user_prompt = f"Please generate a lesson plan based on the following inputs:\n{json.dumps(user_content, indent=2)}"
        
        return self.call_llm_json(system_prompt, user_prompt, LessonPlan, max_retries=2)
