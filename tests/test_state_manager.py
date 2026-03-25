import unittest
import json
from unittest.mock import patch, mock_open
from core.state_manager import StateManager
import os

class TestStateManager(unittest.TestCase):
    @patch('core.state_manager.os.path.exists')
    @patch('core.state_manager.open', new_callable=mock_open)
    def setUp(self, mock_file, mock_exists):
        # Prevent _init_state from trying to write the file
        mock_exists.return_value = True
        self.state_manager = StateManager()

    @patch('core.state_manager.unlock_file')
    @patch('core.state_manager.lock_file')
    @patch('core.state_manager.open', new_callable=mock_open, read_data='{"system_status": "RUNNING"}')
    def test_get_state_success(self, mock_file, mock_lock, mock_unlock):
        state = self.state_manager.get_state()
        self.assertEqual(state, {"system_status": "RUNNING"})
        mock_file.assert_called_once_with(self.state_manager.state_file, 'r')
        mock_lock.assert_called_once()
        mock_unlock.assert_called_once()

    @patch('core.state_manager.logger.error')
    @patch('core.state_manager.open', side_effect=FileNotFoundError("File not found"))
    def test_get_state_file_not_found(self, mock_file, mock_logger):
        state = self.state_manager.get_state()
        self.assertEqual(state, {})
        mock_logger.assert_called_once()
        self.assertTrue(mock_logger.call_args[0][0].startswith("Error reading state file"))

    @patch('core.state_manager.logger.error')
    @patch('core.state_manager.unlock_file')
    @patch('core.state_manager.lock_file')
    @patch('core.state_manager.open', new_callable=mock_open, read_data='invalid json')
    def test_get_state_invalid_json(self, mock_file, mock_lock, mock_unlock, mock_logger):
        state = self.state_manager.get_state()
        self.assertEqual(state, {})
        mock_logger.assert_called_once()
        self.assertTrue(mock_logger.call_args[0][0].startswith("Error reading state file"))


    def test_get_state_corrupted_json_file(self):
        import tempfile
        # Create a temporary file with corrupted JSON
        fd, temp_path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as f:
                f.write('{"system_status": "RUNNING", }') # Invalid JSON due to trailing comma

            # Point state manager to the corrupted file
            self.state_manager.state_file = temp_path

            with patch('core.state_manager.logger.error') as mock_logger:
                state = self.state_manager.get_state()

                # Assert empty dict is returned
                self.assertEqual(state, {})

                # Assert logger was called with an error
                mock_logger.assert_called_once()
                self.assertTrue(mock_logger.call_args[0][0].startswith("Error reading state file"))
        finally:
            os.remove(temp_path)

if __name__ == '__main__':
    unittest.main()
