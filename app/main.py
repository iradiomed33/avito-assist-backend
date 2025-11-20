from fastapi import FastAPI, status, HTTPException
from app.schemas_avito import AvitoWebhook
from app.clients.perplexity_client import PerplexityClient, PerplexityClientError
from app.clients.stt_client import STTClient, STTClientError
from app.token_store import AvitoTokenStore, AvitoTokens
from fastapi.responses import RedirectResponse
from app.clients.avito_client import AvitoMessengerClient, AvitoClientError
from app.settings import avito_settings
from app.clients.avito_auth_client import AvitoAuthClient, AvitoAuthError
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("avito-assist")


app = FastAPI(title="Avito Assist Backend", version="0.1.0")

# Клиенты внешних сервисов инициализируем один раз при старте приложения
perplexity_client = PerplexityClient()
stt_client = STTClient()
avito_auth_client = AvitoAuthClient()
avito_messenger_client = AvitoMessengerClient(base_url=avito_settings.avito_api_base_url)
avito_token_store = AvitoTokenStore()


@app.get("/")
async def health_check():
    """
    Простой health-check эндпоинт для проверки, что сервис жив.
    В ответе вернём статус и версию сервиса.
    """
    return {"status": "ok", "service": "avito-assist-backend", "version": "0.1.0"}


@app.post(
    "/webhooks/avito",
    status_code=status.HTTP_200_OK,
    summary="Avito Messenger webhook endpoint",
)
async def avito_webhook_handler(webhook: AvitoWebhook):
    logger.info(
        "Received Avito webhook: id=%s type=%s chat_id=%s",
        webhook.id,
        webhook.payload.type,
        webhook.payload.value.chat_id,
    )
    """
    Обработчик вебхуков Avito Messenger.

    - различаем типы сообщений: text / voice;
    - для text: отправляем текст в Perplexity;
    - для voice: сначала распознаём речь через STT, затем отправляем
      распознанный текст в Perplexity;
    - при ошибках внешних сервисов (STT/Perplexity/Avito Messenger) не роняем вебхук,
      а возвращаем информацию об ошибке в полях stt_error/assistant_error/messaging_error.
    """
    original_message_type = webhook.payload.value.type
    content = webhook.payload.value.content
    chat_id = webhook.payload.value.chat_id

    # Исходный текст из Avito (для text-сообщений)
    message_text = content.text

    assistant_reply: str | None = None
    assistant_error: str | None = None
    stt_error: str | None = None
    messaging_error: str | None = None
    recognized_text: str | None = None

    # Обработка голосовых сообщений: сначала распознаём речь
    if original_message_type == "voice" and content.audio_url:
        try:
            recognized_text = stt_client.transcribe(content.audio_url)
            # После распознавания используем текст как обычное сообщение
            message_text = recognized_text
        except STTClientError as exc:
            stt_error = str(exc)

    # Если у нас есть какой-то текст (исходный или распознанный) — зовём Perplexity
    if message_text:
        try:
            assistant_reply = perplexity_client.generate_reply(
                user_message=message_text,
                system_prompt=(
                    "Ты ИИ-ассистент для общения в Авито. "
                    "Отвечай кратко, вежливо и по делу."
                ),
            )
        except PerplexityClientError as exc:
            assistant_error = str(exc)

    # Если удалось сгенерировать ответ ассистента — отправляем его в чат Авито
    if assistant_reply:
        # Пробуем взять актуальный access_token из стора
        tokens = avito_token_store.get_default_tokens()
        if not tokens:
            messaging_error = "No Avito access token configured"
        else:
            try:
                avito_messenger_client.send_text_message(
                    chat_id=chat_id,
                    text=assistant_reply,
                    access_token=tokens.access_token,
                )
            except AvitoClientError as exc:
                messaging_error = str(exc)

                if stt_error:
                    logger.error("STT error for chat_id=%s: %s", chat_id, stt_error)
                if assistant_error:
                    logger.error("Perplexity error for chat_id=%s: %s", chat_id, assistant_error)
                if messaging_error:
                    logger.error("Avito messaging error for chat_id=%s: %s", chat_id, messaging_error)

    return {
        "status": "received",
        "webhook_id": webhook.id,
        "event_type": webhook.payload.type,
        # исходный тип сообщения от Avito: "text" или "voice"
        "message_type": original_message_type,
        # исходный текст из Avito (для text), для voice он остаётся None
        "message_text": content.text,
        # текст, полученный из голосового сообщения (для voice)
        "recognized_text": recognized_text,
        "assistant_reply": assistant_reply,
        "assistant_error": assistant_error,
        "stt_error": stt_error,
        "messaging_error": messaging_error,
    }


@app.get("/avito/oauth/start")
async def avito_oauth_start():
    """
    Старт OAuth2-авторизации Авито.

    Редиректит пользователя на страницу авторизации Авито с параметрами:
    - client_id
    - redirect_uri
    - response_type=code
    """
    params = {
        "client_id": avito_settings.avito_client_id,
        "redirect_uri": avito_settings.avito_redirect_uri,
        "response_type": "code",
    }

    # Примерный путь, точный URL нужно выровнять по докам Avito Auth
    auth_url = (
        f"{avito_settings.avito_auth_base_url.rstrip('/')}"
        f"/oauth/authorize"
        f"?client_id={params['client_id']}"
        f"&redirect_uri={params['redirect_uri']}"
        f"&response_type={params['response_type']}"
    )

    return RedirectResponse(url=auth_url)


@app.get("/avito/oauth/callback")
async def avito_oauth_callback(code: str | None = None, error: str | None = None):
    """
    Callback-эндпоинт для приёма authorization_code от Авито.

    - При ошибке авторизации возвращает HTTP 400;
    - При успехе обменивает code на access/refresh токены.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Avito auth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        tokens = avito_auth_client.exchange_code_for_tokens(code)
            # Сохраняем токены в файловом хранилище как "default"
        avito_tokens = AvitoTokens.from_oauth_response(tokens)
        avito_token_store.save_default_tokens(avito_tokens)

    except AvitoAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # TODO: сохранить tokens в хранилище и привязать к пользователю/проекту
    return {"status": "ok", "tokens": tokens}
