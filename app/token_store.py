import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


@dataclass
class AvitoTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime

    @classmethod
    def from_oauth_response(cls, data: Dict[str, Any]) -> "AvitoTokens":
        """
        Создать объект токенов из ответа OAuth Avito.

        Ожидаем как минимум:
        - access_token
        - refresh_token
        - expires_in (секунды)
        """
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        expires_in = int(data.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AvitoTokens":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )


class AvitoTokenStore:
    """
    Простейшее файловое хранилище токенов Avito.

    В MVP храним один набор токенов под ключом "default" в data/avito_tokens.json.
    В будущем можно расширить до нескольких аккаунтов/проектов.
    """

    def __init__(self, path: str = "data/avito_tokens.json") -> None:
        self.path = path
        self._lock = threading.Lock()

    def _load_all(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # При любой ошибке парсинга начинаем с пустого словаря,
            # чтобы не ломать приложение.
            return {}

    def _save_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def save_default_tokens(self, tokens: AvitoTokens) -> None:
        """
        Сохраняет токены как "default".
        """
        with self._lock:
            data = self._load_all()
            data["default"] = tokens.to_dict()
            self._save_all(data)

    def get_default_tokens(self) -> Optional[AvitoTokens]:
        """
        Возвращает токены "default" или None, если их нет.
        """
        with self._lock:
            data = self._load_all()
            raw = data.get("default")
            if not raw:
                return None
            return AvitoTokens.from_dict(raw)
