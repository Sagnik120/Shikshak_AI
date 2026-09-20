import json
from typing import Any, Optional

from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints, LessonPlan


class PlannerAgent(BaseAgent):
    def plan_lesson(
        self,
        constraints: LearnerConstraints,
        source_type: str,
        topic: Optional[str] = None,
        parsed_doc: Optional[Any] = None,
        document_outline: Optional[dict] = None,
        learner_profile: Optional[Any] = None,
    ) -> LessonPlan:
        """Generate a LessonPlan from a topic or from an ingested document."""
        system_prompt = self.load_prompt("planner_system.md")

        user_content: dict[str, Any] = {
            "source_type": source_type,
            "constraints": constraints.model_dump(),
        }

        if topic:
            user_content["topic"] = topic

        if parsed_doc:
            user_content["document_structure"] = getattr(
                parsed_doc, "detected_structure", "Document provided"
            )

        if document_outline:
            # The chapters, key terms and opening excerpts of the uploaded file.
            # Planning a document lesson without these produced a curriculum on
            # whatever subject the model felt like.
            user_content["document"] = document_outline
            user_content["instruction"] = (
                "Plan this lesson strictly from the supplied document. Every concept "
                "must be something the document actually covers. Do not introduce "
                "topics that are absent from it."
            )

        if learner_profile:
            user_content["learner_profile"] = (
                learner_profile.model_dump()
                if hasattr(learner_profile, "model_dump")
                else learner_profile
            )

        user_prompt = (
            "Please generate a lesson plan based on the following inputs:\n"
            f"{json.dumps(user_content, indent=2, ensure_ascii=False)}"
        )

        return self.call_llm_json(system_prompt, user_prompt, LessonPlan, max_retries=2)
