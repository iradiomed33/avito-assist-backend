import os
from datetime import datetime, timedelta, timezone

from app.token_store import AvitoTokenStore, AvitoTokens


def test_avito_token_store_save_and_load(tmp_path):
    path = tmp_path / "tokens.json"
    store = AvitoTokenStore(path=str(path))

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    tokens = AvitoTokens(
        access_token="ACCESS",
        refresh_token="REFRESH",
        expires_at=expires_at,
    )

    store.save_default_tokens(tokens)
    assert os.path.exists(path)

    loaded = store.get_default_tokens()
    assert loaded is not None
    assert loaded.access_token == "ACCESS"
    assert loaded.refresh_token == "REFRESH"
    # по времени просто проверим тип
    assert isinstance(loaded.expires_at, datetime)
