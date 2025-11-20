from fastapi.testclient import TestClient

from app.main import app, avito_auth_client, avito_token_store
from app.token_store import AvitoTokens

client = TestClient(app)


def test_avito_oauth_callback_saves_tokens(monkeypatch, tmp_path):
    # подменяем стор на временный файл
    from app import main as main_module
    main_module.avito_token_store.path = str(tmp_path / "tokens.json")

    def mock_exchange_code_for_tokens(code: str) -> dict:
        assert code == "TEST_CODE"
        return {
            "access_token": "ACCESS123",
            "refresh_token": "REFRESH123",
            "expires_in": 3600,
        }

    monkeypatch.setattr(
        main_module.avito_auth_client,
        "exchange_code_for_tokens",
        mock_exchange_code_for_tokens,
    )

    response = client.get("/avito/oauth/callback", params={"code": "TEST_CODE"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tokens"]["access_token"] == "ACCESS123"

    tokens = main_module.avito_token_store.get_default_tokens()
    assert tokens is not None
    assert tokens.access_token == "ACCESS123"
    assert tokens.refresh_token == "REFRESH123"
