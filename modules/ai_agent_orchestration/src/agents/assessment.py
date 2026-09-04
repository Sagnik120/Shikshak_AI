import json
from typing import List
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult
from modules.ai_agent_orchestration.src.schemas.assessment import AssessmentReport

class AssessmentAgent(BaseAgent):
    def generate_report(
        self,
        lesson_id: str,
        session_history: List[EvaluationResult]
    ) -> AssessmentReport:
        """
        Generate an AssessmentReport for a complete lesson session.
        """
        system_prompt = self.load_prompt("assessment_system.md")
        
        user_content = {
            "lesson_id": lesson_id,
            "session_history": [ev.model_dump() for ev in session_history]
        }
            
        user_prompt = f"Please generate an assessment report based on the following evaluation history:\n{json.dumps(user_content, indent=2)}"
        
        return self.call_llm_json(system_prompt, user_prompt, AssessmentReport, max_retries=2)
