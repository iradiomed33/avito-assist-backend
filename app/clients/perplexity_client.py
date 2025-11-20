import os
import logging
from typing import List, Dict

from perplexity import Perplexity


logger = logging.getLogger(__name__)


class PerplexityClientError(Exception):
    """
    Доменное исключение для ошибок работы с Perplexity API.

    Используется, чтобы отделить ошибки внешнего сервиса от остальных.
    """
    pass


class PerplexityClient:
    """
    Обёртка над официальным SDK Perplexity для работы с Chat Completions API.

    - Берёт API-ключ из окружения PERPLEXITY_API_KEY (или из параметра api_key).
    - Использует модель по умолчанию "sonar".
    """

    def __init__(self, api_key: str | None = None, model: str = "sonar") -> None:
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is not set")

        self._client = Perplexity(api_key=self.api_key)
        self.model = model

    def generate_reply(self, user_message: str, system_prompt: str | None = None) -> str:
        """
        Отправляет запрос в Perplexity Chat Completions и возвращает текст ответа.

        Обработка ошибок:
        - Логируем исключение;
        - Оборачиваем в PerplexityClientError, чтобы верхний слой мог решить,
          что делать (fallback, HTTP-ошибка и т.п.).
        """
        messages: List[Dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_message})

        try:
            completion = self._client.chat.completions.create(
                messages=messages,
                model=self.model,
            )
        except Exception as exc:
            logger.exception("Error while calling Perplexity Chat Completions API")
            raise PerplexityClientError("Failed to get reply from Perplexity") from exc

        try:
            return completion.choices[0].message.content
        except Exception as exc:
            logger.exception("Unexpected response format from Perplexity")
            raise PerplexityClientError("Invalid response format from Perplexity") from exc
