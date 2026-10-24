"""Real OpenRouter call; skipped unless OPENROUTER_API_KEY is set (env or repo .env)."""

import os

import pytest
from dotenv import load_dotenv

from app.trials import REPO_ROOT

load_dotenv(REPO_ROOT / ".env")

pytestmark = pytest.mark.skipif(not os.getenv("OPENROUTER_API_KEY"), reason="no OPENROUTER_API_KEY")


def test_live_turn():
    from app.agent import run_turn
    from app.schemas import ChatMessage, ChatRequest
    from app.service import normalize

    request = ChatRequest(messages=[ChatMessage(role="user", content="I'm 54 with type 2 diabetes in Boston")])
    response = normalize(run_turn(request))
    assert response.assistant_message.strip()
