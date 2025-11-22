import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_404_not_found():
    """Тест обработки 404 ошибки"""
    response = client.get("/nonexistent-endpoint")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "http_error"
    assert data["status_code"] == 404


def test_validation_error():
    """Тест обработки ошибки валидации"""
    # Отправляем невалидный payload в вебхук
    invalid_payload = {
        "id": "test",
        # Пропускаем обязательные поля
    }
    
    response = client.post("/webhooks/avito", json=invalid_payload)
    
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"


def test_process_time_header():
    """Тест наличия заголовка X-Process-Time"""
    response = client.get("/")
    
    assert "x-process-time" in response.headers
    assert "ms" in response.headers["x-process-time"]
