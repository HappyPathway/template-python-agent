# Cleaned up tests for environment variable handling
import os
import unittest

class TestEnvVarsUnit(unittest.TestCase):
    def test_env_var_exists(self):
        """Test that an environment variable exists and has the correct value."""
        os.environ['TEST_VAR'] = 'test_value'
        self.assertEqual(os.getenv('TEST_VAR'), 'test_value')

    def test_env_var_not_exists(self):
        """Test that a non-existent environment variable returns None."""
        if 'TEST_VAR' in os.environ:
            del os.environ['TEST_VAR']
        self.assertIsNone(os.getenv('TEST_VAR'))

if __name__ == '__main__':
    unittest.main()