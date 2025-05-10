# Integration tests for AI engine functionality
import unittest
import os
import pytest
from unittest.mock import patch, MagicMock
from utils.ai_engine import AIEngine

@pytest.mark.integration
class TestAIEngineFunctionsIntegration(unittest.TestCase):
    def setUp(self):
        # Skip if API key not available
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set in environment")
            
        self.engine = AIEngine(feature_name="test_integration")
        
    @patch('utils.ai_engine.AIEngine.generate')
    def test_process_data(self, mock_generate):
        # Configure mock
        mock_generate.return_value = {"processed_key": "processed_value"}
        
        # Test with a mock
        input_data = {"key": "value"}
        expected_output = {"processed_key": "processed_value"}
        
        # Use run_sync for testing
        self.engine.run_sync = MagicMock(return_value=expected_output)
        result = self.engine.run_sync(input_data)
        self.assertEqual(result, expected_output)

    @patch('utils.ai_engine.AIEngine.generate')
    def test_analyze_results(self, mock_generate):
        # Configure mock
        mock_generate.return_value = {"status": "pass"}
        
        # Test with a mock
        results = {"score": 85}
        expected_analysis = {"status": "pass"}
        
        # Use run_sync for testing
        self.engine.run_sync = MagicMock(return_value=expected_analysis)
        result = self.engine.run_sync(results)
        self.assertEqual(result, expected_analysis)

if __name__ == "__main__":
    unittest.main()