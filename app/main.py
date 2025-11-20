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







logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("avito-assist")


app = FastAPI(title="Avito Assist Backend", version="0.1.0")



templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Клиенты внешних сервисов инициализируем один раз при старте приложения
perplexity_client = PerplexityClient()
stt_client = STTClient()
avito_auth_client = AvitoAuthClient()
avito_messenger_client = AvitoMessengerClient(base_url=avito_settings.avito_api_base_url)
avito_token_store = AvitoTokenStore()
project_store = ProjectStore()

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
        return AvitoWebhookResponse(
            processed=False,
            reason="no_project",
            stt_error=None,
            assistant_error=None,
            messaging_error=None,
        )

    now_utc = datetime.utcnow()
    if not project.enabled or not _is_within_schedule(project, now_utc):
        logger.info(
            "Assistant disabled or out of schedule for project=%s, skipping",
            project.id,
        )
        return AvitoWebhookResponse(
            processed=False,
            reason="assistant_disabled_or_out_of_schedule",
            stt_error=None,
            assistant_error=None,
            messaging_error=None,
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

security = HTTPBasic()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Boogie261002!"  # потом вынесем в .env


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
