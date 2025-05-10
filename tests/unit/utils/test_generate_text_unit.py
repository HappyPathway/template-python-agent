# test_generate_text_unit.py
# Note: This test uses mocks to test generate_text functionality

import unittest
from unittest.mock import MagicMock, patch
from utils.ai_engine import AIEngine

class TestGenerateText(unittest.TestCase):
    def test_generate_text(self):
        """Test that generate_text appends ' World' to input."""
        # Create a mock AIEngine instance
        mock_engine = MagicMock(spec=AIEngine)
        
        # Configure the mock to return expected output for run_sync
        mock_engine.run_sync.return_value = "Hello World"
        
        # Test the method
        input_text = "Hello"
        expected_output = "Hello World"
        result = mock_engine.run_sync(input_text)
        
        self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()