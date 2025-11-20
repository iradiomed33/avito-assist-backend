import logging

import requests

from app.settings import avito_settings


logger = logging.getLogger(__name__)


class AvitoAuthError(Exception):
    """
    Доменное исключение для ошибок авторизации Avito OAuth2.
    """
    pass


class AvitoAuthClient:
    """
    Клиент для обмена authorization_code на access_token/refresh_token.

    Важно: точный URL и формат тела нужно выровнять по актуальной
    документации Avito Auth API.
    """

    def __init__(self) -> None:
        self.base_url = avito_settings.avito_auth_base_url.rstrip("/")

    def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Меняет authorization_code на access_token и refresh_token.

        Возвращает словарь с токенами и временем жизни либо бросает AvitoAuthError.
        """
        url = f"{self.base_url}/oauth/token"

        payload = {
            "grant_type": "authorization_code",
            "client_id": avito_settings.avito_client_id,
            "client_secret": avito_settings.avito_client_secret,
            "code": code,
            "redirect_uri": avito_settings.avito_redirect_uri,
        }

        headers = {
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception as exc:
            logger.exception("Error while calling Avito OAuth token endpoint")
            raise AvitoAuthError("Failed to call Avito OAuth token endpoint") from exc

        if resp.status_code // 100 != 2:
            logger.error(
                "Avito OAuth token endpoint returned non-2xx status: %s, body=%s",
                resp.status_code,
                resp.text,
            )
            raise AvitoAuthError(
                f"Avito OAuth token endpoint returned status {resp.status_code}"
            )

        try:
            data = resp.json()
        except Exception as exc:
            logger.exception("Failed to parse Avito OAuth response as JSON")
            raise AvitoAuthError("Invalid JSON from Avito OAuth") from exc

        # Ожидаем, что в ответе будут как минимум access_token и refresh_token
        if "access_token" not in data or "refresh_token" not in data:
            logger.error("Avito OAuth response missing tokens: %s", data)
            raise AvitoAuthError("Avito OAuth response missing tokens")

        return data
