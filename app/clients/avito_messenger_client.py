import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AvitoMessengerClient:
    USER_ID = "107238239"
    
    def get_chats(self, access_token: str, limit: int = 20) -> List[Dict]:
        url = f"https://api.avito.ru/messenger/v2/accounts/{self.USER_ID}/chats"
        params = {"limit": limit}
        resp = self._request("GET", url, access_token, params)
        return resp.get("chats", [])
    
    def get_messages(self, access_token: str, chat_id: str, limit: int = 10) -> List[Dict]:
        url = f"https://api.avito.ru/messenger/v3/accounts/{self.USER_ID}/chats/{chat_id}/messages"
        params = {"limit": limit}
        resp = self._request("GET", url, access_token, params)
        return resp
    
    def send_text(self, access_token: str, chat_id: str, text: str) -> Dict:
        url = f"https://api.avito.ru/messenger/v1/accounts/{self.USER_ID}/chats/{chat_id}/messages"
        payload = {"type": "text", "message": {"text": text}}
        return self._request("POST", url, access_token, json=payload)
    
    def _request(self, method: str, url: str, access_token: str, **kwargs) -> Dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        if kwargs.get("json"):
            headers["Content-Type"] = "application/json"
            
        resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()
