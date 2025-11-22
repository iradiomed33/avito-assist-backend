from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "avito-assist-backend"
    assert data["version"] == "0.1.0"


def test_avito_webhook_basic(monkeypatch):
    from app import main as main_module

    def mock_send_text_message(chat_id: str, text: str, access_token: str) -> None:
        # Проверим, что вызывается с ожидемыми параметрами
        assert chat_id == "chat_1"
        assert text == "Привет, это тестовое сообщение" or isinstance(text, str)
        assert isinstance(access_token, str)

    monkeypatch.setattr(
        main_module.avito_messenger_client,
        "send_text_message",
        mock_send_text_message,
    )

    payload = {
        "id": "wh_123",
        "version": 1,
        "timestamp": "2025-01-01T12:00:00Z",
        "payload": {
            "type": "message",
            "value": {
                "id": "msg_1",
                "chat_id": "chat_1",
                "user_id": "user_1",
                "author_id": "user_1",
                "created": "2025-01-01T12:00:00Z",
                "type": "text",
                "content": {
                    "text": "Привет, это тестовое сообщение"
                }
            }
        }
    }

    response = client.post("/webhooks/avito", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["webhook_id"] == "wh_123"
    assert data["event_type"] == "message"
    assert data["message_type"] == "text"
    assert data["message_text"] == "Привет, это тестовое сообщение"
    assert "assistant_reply" in data
    assert isinstance(data["assistant_reply"], str) or data["assistant_reply"] is None
    assert "assistant_error" in data


def test_avito_webhook_with_mocked_perplexity_success(monkeypatch):
    from app import main as main_module

    def mock_generate_reply(user_message: str, system_prompt: str | None = None) -> str:
        return f"[MOCKED] {user_message}"

    def mock_send_text_message(chat_id: str, text: str, access_token: str) -> None:
        assert chat_id == "chat_2"
        assert text == "[MOCKED] Тест для моков"
        assert isinstance(access_token, str)

    monkeypatch.setattr(
        main_module.perplexity_client,
        "generate_reply",
        mock_generate_reply,
    )
    monkeypatch.setattr(
        main_module.avito_messenger_client,
        "send_text_message",
        mock_send_text_message,
    )

    payload = {
        "id": "wh_456",
        "version": 1,
        "timestamp": "2025-01-01T12:10:00Z",
        "payload": {
            "type": "message",
            "value": {
                "id": "msg_2",
                "chat_id": "chat_2",
                "user_id": "user_2",
                "author_id": "user_2",
                "created": "2025-01-01T12:10:00Z",
                "type": "text",
                "content": {
                    "text": "Тест для моков"
                }
            }
        }
    }

    response = client.post("/webhooks/avito", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["assistant_reply"] == "[MOCKED] Тест для моков"
    assert data["assistant_error"] is None


def test_avito_webhook_with_mocked_perplexity_error(monkeypatch):
    """
    Тестируем сценарий ошибки Perplexity:
    generate_reply выбрасывает PerplexityClientError,
    проверяем, что вебхук не падает и assistant_error заполнен.
    """
    from app import main as main_module
    from app.clients.perplexity_client import PerplexityClientError

    def mock_generate_reply_raises(user_message: str, system_prompt: str | None = None) -> str:
        raise PerplexityClientError("Test-induced failure")

    monkeypatch.setattr(
        main_module.perplexity_client,
        "generate_reply",
        mock_generate_reply_raises,
    )

    payload = {
        "id": "wh_789",
        "version": 1,
        "timestamp": "2025-01-01T12:20:00Z",
        "payload": {
            "type": "message",
            "value": {
                "id": "msg_3",
                "chat_id": "chat_3",
                "user_id": "user_3",
                "author_id": "user_3",
                "created": "2025-01-01T12:20:00Z",
                "type": "text",
                "content": {
                    "text": "Тест ошибки Perplexity"
                }
            }
        }
    }

    response = client.post("/webhooks/avito", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["assistant_reply"] is None
    assert data["assistant_error"] == "Test-induced failure"


def test_avito_webhook_voice_with_mocked_stt_and_perplexity(monkeypatch):
    """
    Голосовое сообщение:
    - STT успешно распознаёт текст;
    - Perplexity успешно возвращает ответ.
    """
    from app import main as main_module

    def mock_transcribe(audio_url: str) -> str:
        assert audio_url == "https://example.com/audio.ogg"
        return "Распознанный текст голоса"

    def mock_generate_reply(user_message: str, system_prompt: str | None = None) -> str:
        assert user_message == "Распознанный текст голоса"
        return "[MOCKED] Ответ на голос"

    monkeypatch.setattr(main_module.stt_client, "transcribe", mock_transcribe)
    monkeypatch.setattr(main_module.perplexity_client, "generate_reply", mock_generate_reply)

    payload = {
        "id": "wh_voice_1",
        "version": 1,
        "timestamp": "2025-01-01T13:00:00Z",
        "payload": {
            "type": "message",
            "value": {
                "id": "msg_voice_1",
                "chat_id": "chat_1",
                "user_id": "user_1",
                "author_id": "user_1",
                "created": "2025-01-01T13:00:00Z",
                "type": "voice",
                "content": {
                    "text": None,
                    "audio_url": "https://example.com/audio.ogg",
                    "duration_ms": 12000
                }
            }
        }
    }

    response = client.post("/webhooks/avito", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message_type"] == "voice"
    assert data["message_text"] is None
    assert data["recognized_text"] == "Распознанный текст голоса"
    assert data["assistant_reply"] == "[MOCKED] Ответ на голос"
    assert data["assistant_error"] is None
    assert data["stt_error"] is None


def test_avito_webhook_voice_stt_error(monkeypatch):
    """
    Голосовое сообщение:
    - STT выбрасывает ошибку;
    - Perplexity не вызывается;
    - в ответе присутствует stt_error.
    """
    from app import main as main_module
    from app.clients.stt_client import STTClientError

    def mock_transcribe_raises(audio_url: str) -> str:
        raise STTClientError("STT test failure")

    def mock_generate_reply(user_message: str, system_prompt: str | None = None) -> str:
        raise AssertionError("Perplexity should not be called when STT fails")

    monkeypatch.setattr(main_module.stt_client, "transcribe", mock_transcribe_raises)
    monkeypatch.setattr(main_module.perplexity_client, "generate_reply", mock_generate_reply)

    payload = {
        "id": "wh_voice_2",
        "version": 1,
        "timestamp": "2025-01-01T13:10:00Z",
        "payload": {
            "type": "message",
            "value": {
                "id": "msg_voice_2",
                "chat_id": "chat_2",
                "user_id": "user_2",
                "author_id": "user_2",
                "created": "2025-01-01T13:10:00Z",
                "type": "voice",
                "content": {
                    "text": None,
                    "audio_url": "https://example.com/audio2.ogg",
                    "duration_ms": 8000
                }
            }
        }
    }

    response = client.post("/webhooks/avito", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message_type"] == "voice"
    assert data["recognized_text"] is None
    assert data["assistant_reply"] is None
    assert data["stt_error"] == "STT test failure"


def test_avito_oauth_start_redirect():
    response = client.get("/avito/oauth/start", follow_redirects=False)
    # FastAPI RedirectResponse по умолчанию 307 или 302
    assert response.status_code in (302, 307)
    location = response.headers.get("location")
    assert location is not None
    assert "client_id=" in location
    assert "redirect_uri=" in location
    assert "response_type=code" in location


def test_avito_oauth_callback_success(monkeypatch):
    from app import main as main_module

    def mock_exchange_code_for_tokens(code: str) -> dict:
        assert code == "TEST_CODE"
        return {
            "access_token": "ACCESS",
            "refresh_token": "REFRESH",
            "expires_in": 3600,
        }

    monkeypatch.setattr(
        main_module.avito_auth_client,
        "exchange_code_for_tokens",
        mock_exchange_code_for_tokens,
    )

    response = client.get("/avito/oauth/callback?code=TEST_CODE")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tokens"]["access_token"] == "ACCESS"
    assert data["tokens"]["refresh_token"] == "REFRESH"

