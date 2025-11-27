import os
import requests
from fastapi import FastAPI, status, HTTPException, Form, Depends, Request
from app.schemas_avito import AvitoWebhook
from app.clients.perplexity_client import PerplexityClient, PerplexityClientError
from app.clients.stt_client import STTClient, STTClientError
from app.token_store import AvitoTokenStore, AvitoTokens
from fastapi.responses import RedirectResponse, HTMLResponse
from app.clients.avito_client import AvitoMessengerClient, AvitoClientError
from app.settings import avito_settings
from app.clients.avito_auth_client import AvitoAuthClient, AvitoAuthError
import logging
from app.projects.models import Project
from app.projects.store import ProjectStore
from typing import List
from datetime import datetime
import zoneinfo
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from app.avito_item_client import AvitoItemClient
from app.prompts import build_system_prompt
from datetime import timezone
from app.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.middleware import RequestLoggingMiddleware
from app.logging_config import setup_logging
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
from app.chat_state import ChatState
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD must be set in .env file!")

setup_logging(
    level="INFO",
    json_logs=False,  # Для прода поставь True
    log_file="logs/avito-assist.log",  # Опционально
)
logger = logging.getLogger("avito-assist")


app = FastAPI(title="Avito Assist Backend", version="0.1.0")

app.add_middleware(RequestLoggingMiddleware)

# Подключаем error handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Клиенты внешних сервисов инициализируем один раз при старте приложения
perplexity_client = PerplexityClient()
stt_client = STTClient()
avito_auth_client = AvitoAuthClient()
avito_messenger_client = AvitoMessengerClient(base_url=avito_settings.avito_api_base_url)
avito_token_store = AvitoTokenStore()
project_store = ProjectStore()
chat_state = ChatState()
avito_messenger_client = AvitoMessengerClient()


async def avito_auto_poller():
    """Поллер: чаты → Perplexity → автоответ каждые 30 сек"""
    try:
        tokens = avito_token_store.get_default_tokens()
        chats = avito_messenger_client.get_chats(tokens.access_token, unread_only=True)
        
        for chat in chats[:3]:  # 3 активных чата
            chat_id = chat["id"]
            messages = avito_messenger_client.get_messages(tokens.access_token, chat_id, limit=3)
            
            # Последнее сообщение клиента (direction="in")
            last_client_msg = next((m for m in reversed(messages) if m.get("direction") == "in"), None)
            if last_client_msg:
                client_text = last_client_msg["content"]["text"]
                logger.info(f"Новое сообщение в {chat_id}: {client_text}")
                
                # Perplexity генерирует ответ
                ai_response = await perplexity_ask(f"Клиент: {client_text}\nОтветь как продавец телескопов:")
                
                # Отправляем!
                result = avito_messenger_client.send_text(tokens.access_token, chat_id, ai_response)
                logger.info(f"✅ Отправлен автоответ: {ai_response}")
                
                # Помечаем прочитанным
                avito_messenger_client.mark_read(tokens.access_token, chat_id)
                
    except Exception as e:
        logger.error(f"Поллер ошибка: {e}")

# Запуск при старте приложения
@app.on_event("startup")
async def startup_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(avito_auto_poller, "interval", seconds=30)
    scheduler.start()
    logger.info("🚀 Автоответчик запущен! Каждые 30 сек")

def _is_within_schedule(project: Project, now_utc: datetime) -> bool:
    """
    Проверяет, попадает ли текущее время в рабочие интервалы проекта.
    """
    if project.schedule_mode == "always":
        return True

    tz = zoneinfo.ZoneInfo(project.timezone)
    now_local = now_utc.astimezone(tz)
    weekday = now_local.weekday()  # 0=Mon ... 6=Sun
    time_str = now_local.strftime("%H:%M")

    day_map = {
        0: project.schedule.mon,
        1: project.schedule.tue,
        2: project.schedule.wed,
        3: project.schedule.thu,
        4: project.schedule.fri,
        5: project.schedule.sat,
        6: project.schedule.sun,
    }
    ranges: List[TimeRange] = day_map.get(weekday, [])

    for r in ranges:
        if r.start <= time_str <= r.end:
            return True
    return False

def ensure_default_project() -> None:
    existing = project_store.get_project("default")
    if existing:
        return
    default_project = Project(
        id="default",
        name="Default project",
        business_type="services",
    )
    project_store.upsert_project(default_project)

ensure_default_project()


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

    project = project_store.get_project("default")
    if not project:
        logger.error("No default project configured, skipping webhook")
        return {
            "processed": False,
            "reason": "no_project",
            "stt_error": None,
            "assistant_error": None,
            "messaging_error": None,
        }

    now_utc = datetime.now(timezone.utc)
    if not project.enabled or not _is_within_schedule(project, now_utc):
        logger.info(
            "Assistant disabled or out of schedule for project=%s, skipping",
            project.id,
        )
        return {
            "processed": False,
            "reason": "no_project",
            "stt_error": None,
            "assistant_error": None,
            "messaging_error": None,
        }
     # Пока не получаем context — будем добавлять позже, когда Авито одобрит приложение
    item_context_str = ""
    author_id = webhook.payload.value.author_id
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
            system_prompt = build_system_prompt(project, item_context="")
    
            assistant_reply = perplexity_client.generate_reply(
                user_message=message_text,
                system_prompt=system_prompt,
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
    """
    client_id = avito_settings.avito_client_id
    redirect_uri = avito_settings.avito_redirect_uri

    if not client_id or not redirect_uri:
        raise HTTPException(status_code=500, detail="Avito OAuth not configured")

    scope = "messenger:read,messenger:write,items:info,user:read"

    auth_url = (
        "https://avito.ru/oauth"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&scope={scope}"
        f"&redirect_uri={redirect_uri}"
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

    return RedirectResponse(url="/ui/project", status_code=303)

security = HTTPBasic()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")  # потом вынесем в .env

if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD must be set in .env file!")


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/admin/projects", response_model=List[Project])
def list_projects(current_admin: str = Depends(get_current_admin)):
    return project_store.list_projects()


@app.get("/admin/projects/{project_id}", response_model=Project)
def get_project(project_id: str, current_admin: str = Depends(get_current_admin)):
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/admin/projects/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    project: Project,
    current_admin: str = Depends(get_current_admin),
):
    if project.id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    project_store.upsert_project(project)
    return project

@app.get("/admin/debug/avito-self")
async def debug_avito_self(current_admin: str = Depends(get_current_admin)):
    """
    Debug-эндпоинт: проверяет актуальность access_token через GET /core/v1/accounts/self
    """
    tokens = avito_token_store.get_default_tokens()
    if not tokens:
        raise HTTPException(status_code=404, detail="No Avito tokens found")
    
    url = f"{avito_settings.avito_api_base_url}/core/v1/accounts/self"
    headers = {
        "Authorization": f"Bearer {tokens.access_token}",
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        return {
            "status": "ok",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code == 200 else resp.text,
            "expires_at": tokens.expires_at.isoformat(),
        }
    except Exception as exc:
        logger.exception("Failed to call Avito /core/v1/accounts/self")
        raise HTTPException(status_code=502, detail=str(exc))

# Debug endpoint
@app.get("/admin/debug/chats")
async def debug_chats(current_admin: str = Depends(get_current_admin)):
    tokens = avito_token_store.get_default_tokens()
    chats = avito_messenger_client.get_chats(tokens.access_token, limit=5)
    return {"user_id": avito_messenger_client.user_id, "chats": chats}

@app.get("/admin/debug/chat/{chat_id}/messages")
async def debug_chat_messages(chat_id: str, current_admin: str = Depends(get_current_admin)):
    tokens = avito_token_store.get_default_tokens()
    messages = avito_messenger_client.get_messages(tokens.access_token, chat_id, limit=5)
    return {"chat_id": chat_id, "messages": messages[:3]}

@app.post("/admin/debug/chat/{chat_id}/send")
async def debug_send_message(chat_id: str, text: str, current_admin: str = Depends(get_current_admin)):
    tokens = avito_token_store.get_default_tokens()
    result = avito_messenger_client.send_text(tokens.access_token, chat_id, text)
    return {"sent": result}


@app.get("/ui/project", response_class=HTMLResponse)
async def ui_get_project(
    request: Request,
    current_admin: str = Depends(get_current_admin),
):
    project = project_store.get_project("default")
    return templates.TemplateResponse(
        "project.html",
        {
            "request": request,
            "project": project,
        },
    )



@app.post("/ui/project")
async def ui_update_project(
    request: Request,
    id: str = Form(...),
    name: str = Form(...),
    business_type: str = Form(...),
    timezone: str = Form(...),
    enabled: bool = Form(False),
    schedule_mode: str = Form(...),
    tone: str = Form(...),
    allow_price_discussion: bool = Form(False),
    extra_instructions: str = Form(""),
    current_admin: str = Depends(get_current_admin),
):

    project = project_store.get_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = name
    project.business_type = business_type  # доверяем HTML‑select
    project.timezone = timezone
    project.enabled = enabled
    project.schedule_mode = schedule_mode  # "always" или "by_schedule"
    project.tone = tone
    project.allow_price_discussion = allow_price_discussion
    project.extra_instructions = extra_instructions or None

    project_store.upsert_project(project)

    return RedirectResponse(url="/ui/project", status_code=303)
