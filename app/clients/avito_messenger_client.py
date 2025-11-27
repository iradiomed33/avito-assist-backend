"""
Avito Messenger API Client
Полный цикл: чаты → сообщения → отправка
"""

import requests
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AvitoMessengerClient:
    def __init__(self, user_id: str = "107238239"):
        self.user_id = user_id
        self.base_url = "https://api.avito.ru"
    
    def get_chats(self, access_token: str, limit: int = 10, unread_only: bool = False) -> List[Dict]:
        """Получить список чатов"""
        url = f"{self.base_url}/messenger/v2/accounts/{self.user_id}/chats"
        params = {
            "limit": limit,
            "unread_only": unread_only
        }
        resp = self._request("GET", url, access_token, params=params)
        return resp.get("chats", [])
    
    def get_messages(self, access_token: str, chat_id: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        """Получить сообщения чата (V3 - не помечает прочитанным)"""
        url = f"{self.base_url}/messenger/v3/accounts/{self.user_id}/chats/{chat_id}/messages"
        params = {"limit": limit, "offset": offset}
        resp = self._request("GET", url, access_token, params=params)
        return resp  # Возвращает массив сообщений
    
    def send_text(self, access_token: str, chat_id: str, text: str) -> Dict:
        """Отправить текстовое сообщение"""
        url = f"{self.base_url}/messenger/v1/accounts/{self.user_id}/chats/{chat_id}/messages"
        payload = {
            "message": {"text": text},
            "type": "text"
        }
        return self._request("POST", url, access_token, json=payload)
    
    def mark_read(self, access_token: str, chat_id: str) -> Dict:
        """Отметить чат прочитанным"""
        url = f"{self.base_url}/messenger/v1/accounts/{self.user_id}/chats/{chat_id}/read"
        return self._request("POST", url, access_token)
    
    def subscribe_webhook(self, access_token: str, webhook_url: str) -> Dict:
        """Подписка на webhook"""
        url = f"{self.base_url}/messenger/v3/webhook"
        payload = {"url": webhook_url}
        return self._request("POST", url, access_token, json=payload)
    
    def _request(self, method: str, url: str, access_token: str, **kwargs) -> Dict:
        """Универсальный запрос с обработкой ошибок"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
