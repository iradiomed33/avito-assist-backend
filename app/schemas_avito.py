from typing import Optional

from pydantic import BaseModel


class AvitoMessageContent(BaseModel):
    """
    Содержимое сообщения.

    Для текстовых сообщений Avito Messenger:
    - content.text — текст сообщения.

    Для голосовых сообщений (voice):
    - audio_url      — URL или идентификатор аудиофайла, по которому его можно скачать;
    - duration_ms    — длительность сообщения в миллисекундах (если даёт Avito).

    В реальной интеграции имена полей audio_url/duration_ms нужно
    выровнять с фактическим форматом Avito Messenger.
    """
    text: Optional[str] = None
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None



class AvitoMessageValue(BaseModel):
    """
    Объект сообщения в payload.value согласно схеме Avito Messenger webhook.

    Основные поля:
    - id         — идентификатор сообщения;
    - chat_id    — идентификатор чата;
    - user_id    — идентификатор пользователя (клиента);
    - author_id  — идентификатор автора сообщения;
    - created    — дата/время создания сообщения (строка в формате ISO);
    - type       — тип сообщения: text, voice, image и т.п.;
    - content    — вложенный объект с реальным содержимым (text и др.).
    """
    id: str | int
    chat_id: str
    user_id: str | int
    author_id: str | int
    created: str | int
    type: str
    content: AvitoMessageContent


class AvitoWebhookPayload(BaseModel):
    """
    Верхнеуровневый payload вебхука Avito.

    - type  — тип вебхука (например, \"message\");
    - value — объект с данными конкретного события (сообщение, чат и т.п.).
    """
    type: str
    value: AvitoMessageValue


class AvitoWebhook(BaseModel):
    """
    Полная модель тела вебхука Avito.

    - id        — идентификатор вебхука;
    - version   — версия;
    - timestamp — время отправки вебхука;
    - payload   — объект с типом и данными события.
    """
    id: str
    version: int | str
    timestamp: str | int
    payload: AvitoWebhookPayload
