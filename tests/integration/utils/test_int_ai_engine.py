"""
Integration tests for the AI Engine.
"""

import os

import pytest

from ailf.ai_engine import AIEngine


@pytest.mark.integration
@pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="OpenAI API key not available"
)
class TestAIEngineIntegration:
    """Integration tests for the AI Engine with actual API calls."""

    def test_openai_connection(self):
        """Test connection to OpenAI API."""
        engine = AIEngine(provider="openai", model="gpt-3.5-turbo")
        health = engine.health_check()
        assert health is True

    @pytest.mark.skip(reason="Would make actual API calls and incur costs")
    def test_generate_text(self):
        """Test generating text with OpenAI."""
        engine = AIEngine(provider="openai", model="gpt-3.5-turbo")
        result = engine.generate_text("Hello, how are you?")
        assert isinstance(result, str)
        assert len(result) > 0
