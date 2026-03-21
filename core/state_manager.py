import json
import os
import logging
from config.settings import config
from datetime import datetime
import platform

# Platforma bağımlı dosya kilitleme
if platform.system() == 'Windows':
    import msvcrt
    def lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def unlock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl
    def lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX)
    def unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)

logger = logging.getLogger(__name__)

class StateManager:
    """
    Sistemin anlık durumunu (system_state.json) okuyup yazan,
    çakışmaları (race conditions) önlemek için dosya kilitlemesi yapan sınıf.
    """
    def __init__(self):
        self.state_file = os.path.join(config.DATA_DIR, "system_state.json")
        self._init_state()

    def _init_state(self):
        if not os.path.exists(self.state_file):
            initial_state = {
                "system_status": "STARTING",
                "last_run": None,
                "data_fetching": False,
                "analyzing": False,
                "emergency_halt": False
            }
            with open(self.state_file, 'w') as f:
                json.dump(initial_state, f, indent=4)
            logger.info("System state initialized.")

    def get_state(self):
        """Mevcut durumu JSON olarak okur."""
        try:
            with open(self.state_file, 'r') as f:
                lock_file(f)
                state = json.load(f)
                unlock_file(f)
            return state
        except Exception as e:
            logger.error(f"Error reading state file: {e}")
            return {}

    def update_state(self, key, value):
        """Belirli bir anahtarı güvenli şekilde günceller."""
        try:
            with open(self.state_file, 'r+') as f:
                lock_file(f)
                state = json.load(f)

                state[key] = value
                state['last_updated'] = datetime.now().isoformat()

                # Başa dönüp yeniden yaz
                f.seek(0)
                f.truncate()
                json.dump(state, f, indent=4)

                unlock_file(f)
                logger.debug(f"State updated: {key} = {value}")
                return True
        except Exception as e:
            logger.error(f"Error updating state file: {e}")
            return False
