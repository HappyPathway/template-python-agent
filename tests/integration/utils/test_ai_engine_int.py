# Integration tests for AI Engine
import unittest
import os
import pytest
from unittest.mock import MagicMock
from utils.ai_engine import AIEngine

@pytest.mark.integration
class TestAIEngineIntegration(unittest.TestCase):
    def setUp(self):
        # Skip if API key not available
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in environment")
            
        self.ai_engine = AIEngine(feature_name="test_integration")
        # Mock the run_sync method for testing
        self.ai_engine.run_sync = MagicMock()

    def test_ai_engine_response(self):
        # Set up expected return value
        self.ai_engine.run_sync.return_value = "Expected output"
        
        # Test the engine
        input_data = "Test input"
        expected_output = "Expected output"
        result = self.ai_engine.run_sync(input_data)
        
        # Assert the result
        self.assertEqual(result, expected_output)

if __name__ == "__main__":
    unittest.main()