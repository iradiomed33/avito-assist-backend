import logging
import os
from typing import Tuple

import requests


logger = logging.getLogger(__name__)


class STTClientError(Exception):
    """
    Доменное исключение для ошибок сервиса распознавания речи (STT).
    """
    pass


class STTClient:
    """
    Клиент для сервиса распознавания речи Yandex SpeechKit (синхронное API v1).

    Использует:
    - API-ключ сервисного аккаунта (YANDEX_SPEECHKIT_API_KEY);
    - идентификатор каталога (YANDEX_SPEECHKIT_FOLDER_ID);
    - синхронное распознавание коротких аудио (до 30 секунд).
    """

    STT_ENDPOINT = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def _get_credentials(self) -> Tuple[str, str]:
        """
        Читает креды из переменных окружения.

        Не вызывается при импортировании модуля, только при реальном вызове transcribe,
        чтобы не ломать тесты и другие сценарии.
        """
        api_key = os.environ.get("YANDEX_SPEECHKIT_API_KEY")
        folder_id = os.environ.get("YANDEX_SPEECHKIT_FOLDER_ID")

        if not api_key:
            raise STTClientError("YANDEX_SPEECHKIT_API_KEY is not set")
        if not folder_id:
            raise STTClientError("YANDEX_SPEECHKIT_FOLDER_ID is not set")

        return api_key, folder_id

    def _download_audio(self, audio_url: str) -> bytes:
        """
        Скачивает аудиофайл по указанному URL.

        Предполагается, что audio_url указывает на голосовое сообщение из Avito.
        Если Avito требует авторизации, сюда нужно будет добавить заголовки/токен.
        """
        try:
            resp = requests.get(audio_url, timeout=10)
        except Exception as exc:
            logger.exception("Failed to download audio from %s", audio_url)
            raise STTClientError("Failed to download audio file") from exc

        if resp.status_code != 200:
            logger.error(
                "Failed to download audio from %s, status=%s",
                audio_url,
                resp.status_code,
            )
            raise STTClientError(
                f"Failed to download audio file, status={resp.status_code}"
            )

        return resp.content

    def transcribe(self, audio_url: str) -> str:
        """
        Выполняет распознавание речи через Yandex SpeechKit STT API.

        Шаги:
        - скачиваем аудиофайл по audio_url;
        - отправляем байты в SpeechKit STT API v1;
        - разбираем JSON-ответ, возвращаем текст или бросаем STTClientError.
        """
        api_key, folder_id = self._get_credentials()
        audio_data = self._download_audio(audio_url)

        params = {
            "lang": "ru-RU",
            "topic": "general",
            "folderId": folder_id,
        }

        headers = {
            # Аутентификация через API-ключ сервисного аккаунта
            "Authorization": f"Api-Key {api_key}",
        }

        try:
            resp = requests.post(
                self.STT_ENDPOINT,
                params=params,
                data=audio_data,
                headers=headers,
                timeout=15,
            )
        except Exception as exc:
            logger.exception("Error while calling Yandex SpeechKit STT API")
            raise STTClientError("Failed to call SpeechKit STT API") from exc

        if resp.status_code != 200:
            logger.error(
                "SpeechKit STT returned non-200 status: %s, body=%s",
                resp.status_code,
                resp.text,
            )
            raise STTClientError(
                f"SpeechKit STT returned status {resp.status_code}"
            )

        try:
            payload = resp.json()
        except Exception as exc:
            logger.exception("Failed to parse SpeechKit STT response as JSON")
            raise STTClientError("Invalid JSON from SpeechKit STT") from exc

        # По докам SpeechKit v1, при успехе есть поле result,
        # при ошибке — error_code / error_message
        if payload.get("error_code"):
            logger.error(
                "SpeechKit STT error: %s, message=%s",
                payload.get("error_code"),
                payload.get("error_message"),
            )
            raise STTClientError(
                f"SpeechKit STT error: {payload.get('error_code')}"
            )

        result_text = payload.get("result")
        if not result_text:
            logger.error("SpeechKit STT returned empty result")
            raise STTClientError("SpeechKit STT returned empty result")

        return result_text
