import unittest
import json
from unittest.mock import patch, mock_open
from core.state_manager import StateManager
import os
import tempfile

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


    def test_update_state_success(self):
        # Create a temporary file with valid JSON
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        json.dump({"system_status": "STARTING"}, temp_file)
        temp_file.close()
        temp_file_path = temp_file.name

        try:
            self.state_manager.state_file = temp_file_path
            result = self.state_manager.update_state("system_status", "RUNNING")
            self.assertTrue(result)

            # Read back the file to ensure it was updated
            with open(temp_file_path, 'r') as f:
                state = json.load(f)
                self.assertEqual(state["system_status"], "RUNNING")
                self.assertIn("last_updated", state)
        finally:
            os.unlink(temp_file_path)

    @patch('core.state_manager.logger.error')
    def test_update_state_error(self, mock_logger):
        self.state_manager.state_file = "/path/does/not/exist/system_state.json"
        result = self.state_manager.update_state("system_status", "RUNNING")
        self.assertFalse(result)
        mock_logger.assert_called_once()

if __name__ == '__main__':
    unittest.main()
