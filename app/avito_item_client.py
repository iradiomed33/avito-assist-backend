import httpx
from typing import Optional, Dict, Any



class AvitoItemClient:
    """
    Клиент для работы с Avito Item API.
    Получает информацию об объявлении по item_id.
    """
    
    BASE_URL = "https://api.avito.ru/core/v1"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def get_item_details(self, user_id: int, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает детали объявления.
        
        Args:
            user_id: ID пользователя Avito (владельца объявления)
            item_id: ID объявления
            
        Returns:
            Словарь с данными объявления или None при ошибке
        """
        url = f"{self.BASE_URL}/accounts/{user_id}/items/{item_id}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    print(f"[AvitoItemClient] Item not found: user_id={user_id}, item_id={item_id}")
                    return None
                else:
                    print(f"[AvitoItemClient] Error {response.status_code}: {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"[AvitoItemClient] Timeout getting item {item_id}")
            return None
        except Exception as e:
            print(f"[AvitoItemClient] Unexpected error: {e}")
            return None
    
    def format_item_for_prompt(self, item_data: Dict[str, Any]) -> str:
        """
        Форматирует данные объявления для включения в промпт.
        
        Args:
            item_data: Данные объявления от API
            
        Returns:
            Отформатированная строка с информацией об объявлении
        """
        if not item_data:
            return ""
        
        parts = []
        
        # Название
        if "title" in item_data:
            parts.append(f"Название: {item_data['title']}")
        
        # Описание
        if "description" in item_data:
            desc = item_data["description"][:500]  # Ограничиваем длину
            parts.append(f"Описание: {desc}")
        
        # Цена
        if "price" in item_data:
            price_info = item_data["price"]
            if isinstance(price_info, dict) and "value" in price_info:
                parts.append(f"Цена: {price_info['value']} ₽")
            elif isinstance(price_info, (int, float)):
                parts.append(f"Цена: {price_info} ₽")
        
        # Категория
        if "category" in item_data:
            parts.append(f"Категория: {item_data['category']}")
        
        # Адрес
        if "address" in item_data:
            parts.append(f"Адрес: {item_data['address']}")
        
        return "\n".join(parts)
