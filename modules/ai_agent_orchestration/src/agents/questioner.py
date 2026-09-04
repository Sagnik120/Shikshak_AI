import json
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment
from modules.ai_agent_orchestration.src.schemas.interaction import InteractionEvent

class QuestionerAgent(BaseAgent):
    def generate_question(
        self,
        node: LessonNode,
        recent_segment: TeachingSegment
    ) -> InteractionEvent:
        """
        Generate an InteractionEvent for a LessonNode.
        """
        system_prompt = self.load_prompt("questioner_system.md")
        
        user_content = {
            "node": node.model_dump(),
            "recent_teaching_segment": recent_segment.model_dump()
        }
            
        user_prompt = f"Please generate a question to assess understanding of this node:\n{json.dumps(user_content, indent=2)}"
        
        event = self.call_llm_json(system_prompt, user_prompt, InteractionEvent, max_retries=2)
        
        # Lightweight check to enforce option rules based on type
        if event.type != "mcq" and event.options:
            event.options = []
            
        return event
