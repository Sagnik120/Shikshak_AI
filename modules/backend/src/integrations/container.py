"""Builds the single wired-up set of AI services the application uses."""
import logging
from typing import Any, Optional

from modules.ai_agent_orchestration.src.adapters.gemini_adapter import get_llm_adapter
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.service import AIOperationService
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.avatar_voice.src.service import AvatarVoiceService
from modules.ml_core.src.service import MLCoreService
from modules.rag.src.service import RAGService

logger = logging.getLogger(__name__)

# How much of the source document the planner is shown. Enough to see what the
# document is about, small enough to stay well inside the prompt budget.
OUTLINE_CHAPTERS = 12
OUTLINE_KEY_TERMS = 24
OUTLINE_EXCERPTS = 4
OUTLINE_EXCERPT_CHARS = 700


class RAGClient:
    """Adapts RAGService to the narrow interface the orchestrator expects."""

    def __init__(self, rag_service: RAGService):
        self.rag = rag_service
        # Outlines are derived from an immutable ingested document, so caching
        # avoids re-querying the vector store on every re-plan.
        self._outlines: dict[str, dict] = {}

    def retrieve_context(self, document_id: str, concept: str) -> list[str]:
        result = self.rag.retrieve_context(document_id=document_id, query_text=concept)
        return [chunk.text for chunk in result.chunks]

    def get_document_outline(self, document_id: str) -> Optional[dict]:
        """What the document is about, for planning a lesson from it.

        The planner previously received only the learner's constraints, so a
        document-sourced lesson was planned on an invented topic.
        """
        if document_id in self._outlines:
            return self._outlines[document_id]

        outline = self._build_outline(document_id)
        if outline:
            self._outlines[document_id] = outline
        return outline

    def _build_outline(self, document_id: str) -> Optional[dict]:
        chapters: list[str] = []
        key_terms: list[str] = []

        store = getattr(self.rag, "vector_store", None)
        metadata = None
        if store is not None and hasattr(store, "get_document_metadata"):
            try:
                metadata = store.get_document_metadata(document_id)
            except Exception:
                metadata = None
        if isinstance(metadata, dict):
            chapters = list(metadata.get("chapters") or [])[:OUTLINE_CHAPTERS]
            key_terms = list(metadata.get("key_terms") or [])[:OUTLINE_KEY_TERMS]

        # Pull representative passages so the planner sees the document's actual
        # subject matter, not just its headings.
        excerpts: list[str] = []
        seen: set[str] = set()
        queries = chapters[:OUTLINE_EXCERPTS] or ["overview introduction summary main topic"]
        for query in queries:
            try:
                result = self.rag.retrieve_context(
                    document_id=document_id, query_text=query, top_k=2
                )
            except Exception as exc:
                logger.warning("Outline retrieval failed for %s: %s", document_id, exc)
                continue

            for chunk in result.chunks:
                text = (chunk.text or "").strip()
                if not text or text[:80] in seen:
                    continue
                seen.add(text[:80])
                excerpts.append(text[:OUTLINE_EXCERPT_CHARS])
                if chunk.section_title and chunk.section_title not in chapters:
                    chapters.append(chunk.section_title)
                if len(excerpts) >= OUTLINE_EXCERPTS:
                    break
            if len(excerpts) >= OUTLINE_EXCERPTS:
                break

        if not excerpts and not chapters and not key_terms:
            logger.warning("Could not build an outline for document %s", document_id)
            return None

        return {
            "document_id": document_id,
            "chapters": chapters[:OUTLINE_CHAPTERS],
            "key_terms": key_terms,
            "excerpts": excerpts,
        }


def get_services() -> dict[str, Any]:
    llm_adapter = get_llm_adapter()

    ml_core_service = MLCoreService(llm_adapter=llm_adapter)
    avatar_voice_service = AvatarVoiceService()
    rag_service = RAGService()

    orchestrator = TeacherOrchestrator(
        planner=PlannerAgent(llm_adapter=llm_adapter),
        explainer=ExplainerAgent(llm_adapter=llm_adapter),
        questioner=QuestionerAgent(llm_adapter=llm_adapter),
        controller=AdaptationController(),
        assessor=AssessmentAgent(llm_adapter=llm_adapter),
        rag_client=RAGClient(rag_service),
        ml_core_client=ml_core_service,
        avatar_client=avatar_voice_service,
    )

    return {
        "ai_service": AIOperationService(orchestrator=orchestrator),
        "ml_core_service": ml_core_service,
        "avatar_voice_service": avatar_voice_service,
        "rag_service": rag_service,
    }


services = get_services()
