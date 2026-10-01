import json
import re
from typing import Optional
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment
from modules.ai_agent_orchestration.src.schemas.interaction import InteractionEvent

def _normalise(text: str) -> str:
    """Same normalisation the MCQ grader applies (case, punctuation, labels)."""
    text = (text or "").strip().lower()
    text = re.sub(r"^\(?\s*[a-d0-9]\s*[\).:-]\s+", "", text)
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def _matching_option(event: InteractionEvent) -> Optional[str]:
    """The option the answer key names, or None if it names none of them."""
    key = _normalise(event.expected_concept)
    for option in event.options or []:
        if _normalise(option) == key:
            return option
    return None


class QuestionerAgent(BaseAgent):
    def generate_question(
        self,
        node: LessonNode,
        recent_segment: Optional[TeachingSegment] = None
    ) -> InteractionEvent:
        """
        Generate an InteractionEvent for a LessonNode.
        """
        system_prompt = self.load_prompt("questioner_system.md")
        
        segment_data = {}
        if recent_segment is not None:
            if hasattr(recent_segment, "model_dump"):
                segment_data = recent_segment.model_dump()
            elif isinstance(recent_segment, dict):
                segment_data = recent_segment

        user_content = {
            "node": node.model_dump(),
            "recent_teaching_segment": segment_data
        }
            
        user_prompt = f"Please generate a question to assess understanding of this node:\n{json.dumps(user_content, indent=2)}"
        
        event = self.call_llm_json(system_prompt, user_prompt, InteractionEvent, max_retries=2)
        if event.type != "mcq":
            event.options = []
            return event

        # MCQs are graded by matching the chosen option to expected_concept. A
        # key that is not one of the options marks EVERY learner wrong, correct
        # answers included — so it is enforced here, not trusted.
        key = _matching_option(event)
        if key is None:
            retry = user_prompt + (
                "\n\nYour previous question's expected_concept was not one of its options. "
                "For an mcq, expected_concept must be the correct option copied exactly."
            )
            event = self.call_llm_json(system_prompt, retry, InteractionEvent, max_retries=2)
            if event.type != "mcq":
                event.options = []
                return event
            key = _matching_option(event)
        if key is None:
            # Still no usable key: ask it as a free-text question, which the
            # rubric grader scores against the stated understanding instead.
            return event.model_copy(update={"type": "short_answer", "options": []})
        return event.model_copy(update={"expected_concept": key})
