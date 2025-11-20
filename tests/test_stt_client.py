import json

import pytest

from app.clients.stt_client import STTClient, STTClientError


class DummyResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"", text: str = "", json_data=None):
        self.status_code = status_code
        self.content = content
        self._text = text
        self._json_data = json_data

    @property
    def text(self) -> str:
        return self._text

    def json(self):
        if self._json_data is not None:
            return self._json_data
        return json.loads(self._text)


def make_client_with_env(monkeypatch):
    """
    Создаёт STTClient с подставленными env-переменными для SpeechKit.
    """
    monkeypatch.setenv("YANDEX_SPEECHKIT_API_KEY", "dummy-key")
    monkeypatch.setenv("YANDEX_SPEECHKIT_FOLDER_ID", "dummy-folder")
    return STTClient()


def test_stt_transcribe_success(monkeypatch):
    """
    Успешный сценарий:
    - audio_url скачивается без ошибок;
    - SpeechKit возвращает 200 и JSON с полем "result".
    """
    client = make_client_with_env(monkeypatch)

    def mock_get(url: str, timeout: int = 10):
        assert url == "https://example.com/audio.ogg"
        return DummyResponse(status_code=200, content=b"FAKEOGGDATA")

    def mock_post(url: str, params=None, data=None, headers=None, timeout: int = 15):
        assert url == STTClient.STT_ENDPOINT
        assert params["lang"] == "ru-RU"
        assert params["folderId"] == "dummy-folder"
        assert headers["Authorization"].startswith("Api-Key ")
        return DummyResponse(
            status_code=200,
            json_data={"result": "Привет, это распознанный текст"},
        )

    import app.clients.stt_client as stt_module

    monkeypatch.setattr(stt_module.requests, "get", mock_get)
    monkeypatch.setattr(stt_module.requests, "post", mock_post)

    text = client.transcribe("https://example.com/audio.ogg")
    assert text == "Привет, это распознанный текст"


def test_stt_transcribe_non_200_from_speechkit(monkeypatch):
    """
    SpeechKit вернул не 200 — ожидаем STTClientError.
    """
    client = make_client_with_env(monkeypatch)

    def mock_get(url: str, timeout: int = 10):
        return DummyResponse(status_code=200, content=b"FAKEOGGDATA")

    def mock_post(url: str, params=None, data=None, headers=None, timeout: int = 15):
        return DummyResponse(status_code=500, text="Internal error")

    import app.clients.stt_client as stt_module

    monkeypatch.setattr(stt_module.requests, "get", mock_get)
    monkeypatch.setattr(stt_module.requests, "post", mock_post)

    with pytest.raises(STTClientError) as exc_info:
        client.transcribe("https://example.com/audio.ogg")

    assert "status 500" in str(exc_info.value) or "status 5" in str(exc_info.value)


def test_stt_transcribe_speechkit_error_code(monkeypatch):
    """
    SpeechKit вернул error_code в JSON — ожидаем STTClientError.
    """
    client = make_client_with_env(monkeypatch)

    def mock_get(url: str, timeout: int = 10):
        return DummyResponse(status_code=200, content=b"FAKEOGGDATA")

    def mock_post(url: str, params=None, data=None, headers=None, timeout: int = 15):
        return DummyResponse(
            status_code=200,
            json_data={
                "error_code": "BAD_AUDIO",
                "error_message": "Audio format not supported",
            },
        )

    import app.clients.stt_client as stt_module

    monkeypatch.setattr(stt_module.requests, "get", mock_get)
    monkeypatch.setattr(stt_module.requests, "post", mock_post)

    with pytest.raises(STTClientError) as exc_info:
        client.transcribe("https://example.com/audio.ogg")

    assert "BAD_AUDIO" in str(exc_info.value)


def test_stt_transcribe_empty_result(monkeypatch):
    """
    SpeechKit вернул пустой result — ожидаем STTClientError.
    """
    client = make_client_with_env(monkeypatch)

    def mock_get(url: str, timeout: int = 10):
        return DummyResponse(status_code=200, content=b"FAKEOGGDATA")

    def mock_post(url: str, params=None, data=None, headers=None, timeout: int = 15):
        return DummyResponse(status_code=200, json_data={"result": ""})

    import app.clients.stt_client as stt_module

    monkeypatch.setattr(stt_module.requests, "get", mock_get)
    monkeypatch.setattr(stt_module.requests, "post", mock_post)

    with pytest.raises(STTClientError) as exc_info:
        client.transcribe("https://example.com/audio.ogg")

    assert "empty result" in str(exc_info.value).lower()
