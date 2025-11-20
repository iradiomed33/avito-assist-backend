import logging
import os
from typing import Optional

import requests


logger = logging.getLogger(__name__)


class AvitoClientError(Exception):
    """
    Доменное исключение для ошибок Avito API.
    """
    pass


class AvitoMessengerClient:
    """
    Клиент для работы с Avito Messenger API (отправка сообщений в чаты).

    Для простоты MVP:
    - базовый URL берётся из AVITO_API_BASE_URL или по умолчанию;
    - access_token передаётся в методе явно (в будущем — из хранилища токенов).
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = base_url or os.environ.get(
            "AVITO_API_BASE_URL",
            "https://api.avito.ru",
        )

    def send_text_message(
        self,
        chat_id: str,
        text: str,
        access_token: str,
    ) -> None:
        """
        Отправляет текстовое сообщение в указанный чат Avito Messenger.

        Путь и точное тело запроса нужно будет выровнять по актуальной
        документации Avito Messenger API.

        Сейчас:
        - примерный POST-запрос;
        - выбрасываем AvitoClientError при ошибках.
        """
        # Примерный URL; в бою нужно взять точный endpoint из доков
        url = f"{self.base_url}/messenger/v1/chats/{chat_id}/messages"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "type": "text",
            "message": text,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception as exc:
            logger.exception("Error while calling Avito Messenger send message API")
            raise AvitoClientError("Failed to call Avito Messenger API") from exc

        if resp.status_code // 100 != 2:
            logger.error(
                "Avito Messenger API returned non-2xx status: %s, body=%s",
                resp.status_code,
                resp.text,
            )
            raise AvitoClientError(
                f"Avito Messenger API returned status {resp.status_code}"
            )
