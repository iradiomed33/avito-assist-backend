import pytest


@pytest.fixture
def monkeypatch_session(monkeypatch):
    """
    Удобная обёртка для установки переменных окружения в рамках одного теста.
    """
    return monkeypatch
