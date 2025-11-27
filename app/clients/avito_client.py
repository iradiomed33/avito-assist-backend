import logging
import os
from typing import Optional, List, Dict, Any

import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AvitoClientError(Exception):
    """Доменное исключение для ошибок Avito API."""
    pass

class Chat(BaseModel):
    id: str
    title: str
    unread_count: int
    last_message_time: str

class Message(BaseModel):
    id: str
    type: str  # "text", "voice"
    content: Dict[str, Any]
    time: str
    author_id: str

class AvitoMessengerClient:
    """Клиент для работы с Avito Messenger API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url or os.environ.get(
            "AVITO_API_BASE_URL",
            "https://api.avito.ru",
        )

    def get_chats(self, access_token: str, limit: int = 20) -> List[Chat]:
        """Получить список чатов аккаунта."""
        url = f"{self.base_url}/messenger/v1/chats"  # ← БЕЗ accounts/{id}
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"limit": limit}
        
        resp = self._make_request("GET", url, headers=headers, params=params)
        return [Chat(**chat) for chat in resp]

    def get_chat_messages(
        self, 
        chat_id: str, 
        access_token: str, 
        limit: int = 10,
        since_message_id: Optional[str] = None
    ) -> List[Message]:
        """Получить сообщения чата (с фильтром по времени/ID)."""
        url = f"{self.base_url}/messenger/v1/chats/{chat_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        params = {"limit": limit}
        if since_message_id:
            params["since"] = since_message_id

        resp = self._make_request("GET", url, headers=headers, params=params)
        return [Message(**msg) for msg in resp]

    def send_text_message(
        self,
        chat_id: str,
        text: str,
        access_token: str,
    ) -> None:
        """Отправляет текстовое сообщение в чат."""
        url = f"{self.base_url}/messenger/v1/chats/{chat_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "type": "text",
            "message": text,
        }

        self._make_request("POST", url, headers=headers, json=payload)

    def _make_request(
        self, 
        method: str, 
        url: str, 
        headers: Dict[str, str], 
        params: Optional[Dict] = None,
        json: Optional[Dict] = None
    ) -> Any:
        """Вспомогательный метод для запросов к Avito API."""
        try:
            resp = requests.request(
                method, url, headers=headers, params=params, json=json, timeout=10
            )
        except Exception as exc:
            logger.exception("Error calling Avito API: %s %s", method, url)
            raise AvitoClientError(f"Failed to call Avito API: {method} {url}") from exc

        if resp.status_code // 100 != 2:
            logger.error(
                "Avito API error: %s %s -> %s: %s",
                method, url, resp.status_code, resp.text
            )
            raise AvitoClientError(
                f"Avito API returned {resp.status_code}: {resp.text}"
            )

        try:
            return resp.json()
        except Exception as exc:
            logger.error("Failed to parse Avito API JSON response: %s", resp.text)
            raise AvitoClientError("Invalid JSON from Avito API") from exc
