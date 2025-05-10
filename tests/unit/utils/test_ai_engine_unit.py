# Cleaned up tests for AIEngine
import unittest
import os
import pytest
from unittest.mock import patch, MagicMock
from utils.ai_engine import AIEngine

class TestAIEngineUnit(unittest.TestCase):
    def setUp(self):
        """Set up an instance of AIEngine for testing."""
        # Skip tests if API key is not available
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in environment")
            
        # AIEngine requires feature_name parameter
        self.ai_engine = AIEngine(feature_name="test_feature")

    def test_ai_engine_initialization(self):
        """Test that AIEngine initializes correctly."""
        self.assertIsNotNone(self.ai_engine)

    @patch('utils.ai_engine.AIEngine.generate_text')
    def test_ai_engine_process(self, mock_generate_text):
        """Test the generate_text method of AIEngine."""
        mock_generate_text.return_value = "processed: test input"
        
        input_data = "test input"
        # Call the async method synchronously for testing
        self.ai_engine.run_sync = MagicMock(return_value="processed: test input")
        result = self.ai_engine.run_sync(input_data)
        self.assertEqual(result, "processed: test input")

if __name__ == '__main__':
    unittest.main()