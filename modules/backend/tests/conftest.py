import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from modules.backend.src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_ai_service():
    ai_mock = Mock()
    avatar_mock = Mock()
    
    with patch("modules.backend.src.state.driver.ai_service", ai_mock), \
         patch("modules.backend.src.api.ws.avatar_service", avatar_mock):
        yield ai_mock, avatar_mock
