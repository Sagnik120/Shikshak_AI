import pytest
from typing import List, Dict
from pydantic import BaseModel
from modules.ai_agent_orchestration.src.agents.base import BaseAgent
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

class DummyModel(BaseModel):
    field1: str
    field2: int

def test_llm_adapter_base_agent_json_wrap():
    adapter = FakeLLMAdapter(responses=['{"field1": "hello", "field2": 42}'])
    agent = BaseAgent(adapter)
    
    result = agent.call_llm_json(
        system_prompt="sys",
        user_prompt="usr",
        response_model=DummyModel
    )
    
    assert result.field1 == "hello"
    assert result.field2 == 42
    assert len(adapter.calls) == 1
    assert adapter.calls[0][0]["role"] == "system"
    assert adapter.calls[0][1]["role"] == "user"

def test_llm_adapter_markdown_json_strip():
    adapter = FakeLLMAdapter(responses=['```json\n{"field1": "hello", "field2": 42}\n```'])
    agent = BaseAgent(adapter)
    result = agent.call_llm_json("sys", "usr", DummyModel)
    assert result.field2 == 42

def test_llm_adapter_retry_on_invalid_json():
    # First response invalid, second response valid
    adapter = FakeLLMAdapter(responses=['{"field1": "hello", ', '{"field1": "hello", "field2": 42}'])
    agent = BaseAgent(adapter)
    
    result = agent.call_llm_json("sys", "usr", DummyModel, max_retries=1)
    
    assert result.field2 == 42
    assert len(adapter.calls) == 2
    
def test_llm_adapter_fails_after_retries():
    adapter = FakeLLMAdapter(responses=['{invalid}'] * 5)
    agent = BaseAgent(adapter)
    
    with pytest.raises(ValueError, match="Failed to get valid JSON"):
        agent.call_llm_json("sys", "usr", DummyModel, max_retries=1)
