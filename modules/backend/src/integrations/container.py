import sys
import os

# Stub concrete LLM adapter for hackathon MVP path
try:
    from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
except ImportError:
    # Fallback if tests folder isn't in path
    class FakeLLMAdapter:
        def complete(self, messages, tools=None):
            return "{}"

from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.service import AIOperationService

from modules.ml_core.src.service import MLCoreService
from modules.avatar_voice.src.service import AvatarVoiceService
from modules.rag.src.service import RAGService

# Stub RAG Client for Orchestrator integration
class RAGClientStub:
    def __init__(self, rag_service: RAGService):
        self.rag = rag_service
    def retrieve_context(self, document_id, concept):
        # Delegate to real RAGService
        res = self.rag.retrieve_context(document_id=document_id, query_text=concept)
        return [c.text for c in res.chunks]

def get_services():
    llm_adapter = FakeLLMAdapter()
    
    # Initialize Core Services
    ml_core_service = MLCoreService(llm_adapter=llm_adapter)
    avatar_voice_service = AvatarVoiceService()
    rag_service = RAGService()
    
    # Initialize Orchestrator Agents
    planner = PlannerAgent(llm_adapter=llm_adapter)
    explainer = ExplainerAgent(llm_adapter=llm_adapter)
    questioner = QuestionerAgent(llm_adapter=llm_adapter)
    controller = AdaptationController()
    assessor = AssessmentAgent(llm_adapter=llm_adapter)
    
    rag_client_stub = RAGClientStub(rag_service)
    
    orchestrator = TeacherOrchestrator(
        planner=planner,
        explainer=explainer,
        questioner=questioner,
        controller=controller,
        assessor=assessor,
        rag_client=rag_client_stub,
        ml_core_client=ml_core_service,
        avatar_client=avatar_voice_service
    )
    
    ai_service = AIOperationService(orchestrator=orchestrator)
    
    return {
        "ai_service": ai_service,
        "ml_core_service": ml_core_service,
        "avatar_voice_service": avatar_voice_service,
        "rag_service": rag_service
    }

services = get_services()
