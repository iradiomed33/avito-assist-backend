import pytest
from unittest.mock import AsyncMock, patch
from app.avito_item_client import AvitoItemClient
import pytest

pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_get_item_details_success():
    """Тест успешного получения данных объявления"""
    client = AvitoItemClient(access_token="fake_token")
    
    mock_response = {
        "title": "iPhone 13 Pro 128GB",
        "description": "Состояние отличное, без царапин",
        "price": {"value": 65000, "currency": "RUB"},
        "category": "Телефоны",
        "address": "Москва, м. Сокол"
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=200, json=lambda: mock_response)
        
        result = await client.get_item_details(user_id=12345, item_id=67890)
        
        assert result is not None
        assert result["title"] == "iPhone 13 Pro 128GB"
        assert result["price"]["value"] == 65000


@pytest.mark.asyncio
async def test_get_item_details_not_found():
    """Тест случая, когда объявление не найдено"""
    client = AvitoItemClient(access_token="fake_token")
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(status_code=404, text="Not Found")
        
        result = await client.get_item_details(user_id=12345, item_id=99999)
        
        assert result is None


def test_format_item_for_prompt():
    """Тест форматирования данных объявления для промпта"""
    client = AvitoItemClient(access_token="fake_token")
    
    item_data = {
        "title": "Квартира 2-к",
        "description": "Продаю квартиру в центре, отличный ремонт",
        "price": {"value": 5000000},
        "category": "Недвижимость"
    }
    
    formatted = client.format_item_for_prompt(item_data)
    
    assert "Название: Квартира 2-к" in formatted
    assert "Цена: 5000000 ₽" in formatted
    assert "Категория: Недвижимость" in formatted


def test_format_item_empty():
    """Тест форматирования пустых данных"""
    client = AvitoItemClient(access_token="fake_token")
    
    formatted = client.format_item_for_prompt({})
    
    assert formatted == ""
