import json

import pytest

from app.clients.avito_client import AvitoMessengerClient, AvitoClientError


class DummyResponse:
    def __init__(self, status_code: int = 200, text: str = "", json_data=None):
        self.status_code = status_code
        self._text = text
        self._json_data = json_data

    @property
    def text(self) -> str:
        return self._text

    def json(self):
        if self._json_data is not None:
            return self._json_data
        return json.loads(self._text or "{}")


def test_avito_send_text_message_success(monkeypatch):
    client = AvitoMessengerClient(base_url="https://api.avito.test")

    def mock_post(url: str, json=None, headers=None, timeout: int = 10):
        assert url == "https://api.avito.test/messenger/v1/chats/chat_1/messages"
        assert json == {"type": "text", "message": "Привет из теста"}
        assert headers["Authorization"].startswith("Bearer ")
        return DummyResponse(status_code=200, text="OK")

    import app.clients.avito_client as avito_module

    monkeypatch.setattr(avito_module.requests, "post", mock_post)

    # Если исключения не было — считаем успехом
    client.send_text_message(
        chat_id="chat_1",
        text="Привет из теста",
        access_token="TEST_TOKEN",
    )


def test_avito_send_text_message_non_2xx(monkeypatch):
    client = AvitoMessengerClient(base_url="https://api.avito.test")

    def mock_post(url: str, json=None, headers=None, timeout: int = 10):
        return DummyResponse(status_code=403, text="Forbidden")

    import app.clients.avito_client as avito_module

    monkeypatch.setattr(avito_module.requests, "post", mock_post)

    with pytest.raises(AvitoClientError) as exc_info:
        client.send_text_message(
            chat_id="chat_1",
            text="Привет",
            access_token="TEST_TOKEN",
        )

    assert "status 403" in str(exc_info.value) or "status 4" in str(exc_info.value)
