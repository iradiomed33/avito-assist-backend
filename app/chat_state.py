import json
import os
import threading
from typing import Dict, Optional
from datetime import datetime

class ChatState:
    """Состояние чатов: последний обработанный message_id по chat_id."""
    
    def __init__(self, path: str = "data/chat_state.json"):
        self.path = path
        self._lock = threading.Lock()
        self._state: Dict[str, str] = {}  # chat_id -> last_message_id

    def _load(self) -> Dict[str, str]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def get_last_message_id(self, chat_id: str) -> Optional[str]:
        with self._lock:
            return self._state.get(chat_id)

    def set_last_message_id(self, chat_id: str, message_id: str):
        with self._lock:
            self._state[chat_id] = message_id
            self._save()
