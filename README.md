text
# Avito Assist Backend

**Универсальный ИИ-ассистент для чатов Avito на базе Perplexity API**

Автоматизированный помощник для общения с клиентами в мессенджере Авито. Поддерживает текстовые и голосовые сообщения, настраивается под разные типы бизнеса, работает по расписанию.

---

## 🚀 Возможности

- ✅ **Автоответы в Avito Messenger**: текстовые и голосовые сообщения
- ✅ **Распознавание речи (STT)**: автоматическая обработка голосовых сообщений
- ✅ **ИИ-генерация ответов**: через Perplexity API (llama-3.1-sonar-large-128k-online)
- ✅ **OAuth2 интеграция с Avito**: безопасная авторизация
- ✅ **Настраиваемые промпты**: под разные типы бизнеса (услуги, товары, недвижимость, авто)
- ✅ **Расписание работы**: ассистент работает только в указанное время
- ✅ **Web UI**: простой интерфейс для настройки проекта
- ✅ **Централизованное логирование**: structured logs с JSON форматом
- ✅ **Graceful degradation**: сервис не падает при ошибках внешних API
- ✅ **Unit и integration тесты**: покрытие основных сценариев

---

## 📋 Требования

- **Python**: 3.10 или выше
- **ОС**: Linux (Ubuntu 20.04+), macOS, Windows 10+
- **VPS/VDS**: для продакшена (минимум 1 vCPU, 1 GB RAM)
- **Домен**: для HTTPS и OAuth callback
- **SSL-сертификат**: Let's Encrypt (бесплатно)

---

## 🛠️ Установка и настройка

### 1. Клонирование репозитория

git clone https://github.com/iradiomed33/avito-assist-backend.git
cd avito-assist-backend

text

### 2. Создание виртуального окружения

**Linux/macOS:**
python3 -m venv venv
source venv/bin/activate

text

**Windows (PowerShell):**
python -m venv venv
.\venv\Scripts\Activate.ps1

text

### 3. Установка зависимостей

pip install -r requirements.txt

text

### 4. Настройка переменных окружения

Создай файл `.env` в корне проекта:

Perplexity API
PERPLEXITY_API_KEY=your_perplexity_api_key_here
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online

STT Service
STT_API_KEY=your_stt_api_key_here
STT_API_URL=https://your-stt-service.com/transcribe

Avito OAuth
AVITO_CLIENT_ID=your_avito_client_id
AVITO_CLIENT_SECRET=your_avito_client_secret
AVITO_REDIRECT_URI=https://your-domain.com/avito/oauth/callback

Avito API
AVITO_API_BASE_URL=https://api.avito.ru
AVITO_AUTH_BASE_URL=https://api.avito.ru

Admin UI (измени на свои!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here

text

**Важно**: Добавь `.env` в `.gitignore`, чтобы не закоммитить секреты!

echo ".env" >> .gitignore

text

---

## 🚀 Запуск локально

### Режим разработки (с hot reload)

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

text

Сервис будет доступен:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Web UI настроек: http://localhost:8000/ui/project

### Запуск тестов

pytest # Все тесты
pytest -v # С подробным выводом
pytest tests/test_main.py # Конкретный файл

text

---

## 🌐 Деплой на VDS

### Подготовка сервера (Ubuntu 20.04+)

Обновление системы
sudo apt update && sudo apt upgrade -y

Установка Python 3.10+
sudo apt install -y python3.10 python3.10-venv python3-pip

Установка Git
sudo apt install -y git

Установка Nginx
sudo apt install -y nginx

Установка Certbot (для SSL)
sudo apt install -y certbot python3-certbot-nginx

text

### Клонирование проекта на сервер

cd /opt
sudo git clone https://github.com/iradiomed33/avito-assist-backend.git
cd avito-assist-backend

Создание venv
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

Настройка .env
sudo nano .env # Вставь свои credentials

text

### Настройка systemd сервиса

Создай файл `/etc/systemd/system/avito-assist.service`:

[Unit]
Description=Avito Assist Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/avito-assist-backend
Environment="PATH=/opt/avito-assist-backend/venv/bin"
ExecStart=/opt/avito-assist-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

text

Запуск сервиса:

sudo systemctl daemon-reload
sudo systemctl enable avito-assist
sudo systemctl start avito-assist
sudo systemctl status avito-assist

text

### Настройка Nginx (reverse proxy)

Создай файл `/etc/nginx/sites-available/avito-assist`:

server {
listen 80;
server_name your-domain.com;

text
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
}

text

Активация конфига:

sudo ln -s /etc/nginx/sites-available/avito-assist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

text

### Получение SSL-сертификата

sudo certbot --nginx -d your-domain.com

text

Certbot автоматически настроит HTTPS и редирект с HTTP.

---

## 🔧 Настройка Avito OAuth

### 1. Регистрация приложения

1. Перейди на [Портал разработчика Avito](https://developers.avito.ru)
2. Создай новое приложение в разделе "Мои приложения"
3. Укажи Redirect URI: `https://your-domain.com/avito/oauth/callback`
4. Получи `CLIENT_ID` и `CLIENT_SECRET`
5. Вставь их в `.env`

### 2. Запрос доступа к Messenger API

В описании приложения укажи:

> Интеграция ИИ-ассистента с Avito Messenger для автоматизации общения с клиентами. Требуется доступ для чтения входящих сообщений и отправки исходящих от имени аккаунта через API.

Авито одобрит заявку в течение 1-3 рабочих дней.

### 3. Получение токенов

После одобрения перейди на:

https://your-domain.com/avito/oauth/start

text

Авторизуйся и разреши доступ. Токены автоматически сохранятся.

---

## 📖 API Endpoints

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Health check |
| `POST` | `/webhooks/avito` | Вебхук для Avito Messenger |
| `GET` | `/avito/oauth/start` | Старт OAuth авторизации |
| `GET` | `/avito/oauth/callback` | Callback для OAuth |
| `GET` | `/ui/project` | Web UI настроек проекта |
| `POST` | `/ui/project` | Сохранение настроек |

### Admin API (требует Basic Auth)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/admin/projects` | Список проектов |
| `GET` | `/admin/projects/{id}` | Детали проекта |
| `PUT` | `/admin/projects/{id}` | Обновление проекта |

---

## 🧪 Тестирование

### Структура тестов

tests/
├── test_main.py # Тесты вебхука и эндпоинтов
├── test_prompts.py # Тесты промптов
├── test_avito_item_client.py # Тесты Item API клиента
├── test_error_handlers.py # Тесты обработки ошибок
└── test_avito_oauth_callback.py # Тесты OAuth

text

### Запуск с покрытием

pip install pytest-cov
pytest --cov=app --cov-report=html

text

Отчёт будет в `htmlcov/index.html`.

---

## 📊 Логирование

### Структура логов

Логи пишутся в:
- **Консоль**: цветной вывод для разработки
- **Файл**: `logs/avito-assist.log` (опционально)

### Уровни логирования

- `DEBUG`: детальная отладочная информация
- `INFO`: нормальные события (запросы, ответы)
- `WARNING`: предупреждения (внешние API недоступны)
- `ERROR`: ошибки обработки
- `CRITICAL`: критические ошибки системы

### Просмотр логов на VDS

Логи systemd
sudo journalctl -u avito-assist -f

Логи в файл
tail -f logs/avito-assist.log

text

---

## 🔐 Безопасность

1. **Никогда не коммить `.env` файл**
2. **Использовать strong passwords** для Admin UI
3. **Ограничить доступ к `/admin/*` через Nginx** (whitelist IP)
4. **Регулярно обновлять зависимости**: `pip list --outdated`
5. **Мониторить логи** на подозрительную активность

---

## 🛠️ Разработка

### Структура проекта

avito-assist-backend/
├── app/
│ ├── clients/ # Клиенты внешних API
│ │ ├── perplexity_client.py
│ │ ├── stt_client.py
│ │ ├── avito_client.py
│ │ └── avito_auth_client.py
│ ├── projects/ # Модели проектов
│ │ ├── models.py
│ │ └── store.py
│ ├── avito_item_client.py # Клиент Item API
│ ├── error_handlers.py # Обработчики ошибок
│ ├── logging_config.py # Конфигурация логов
│ ├── middleware.py # Middleware
│ ├── prompts.py # Генерация промптов
│ ├── main.py # FastAPI приложение
│ ├── schemas_avito.py # Pydantic схемы
│ ├── settings.py # Настройки
│ └── token_store.py # Хранение токенов
├── tests/ # Unit-тесты
├── templates/ # HTML шаблоны
├── static/ # Статика (CSS, JS)
├── logs/ # Логи
├── data/ # Данные (токены, проекты)
├── .env # Переменные окружения
├── requirements.txt # Зависимости
└── README.md # Документация

text

### Git workflow

Создание ветки
git checkout -b feature/new-feature

Коммит
git add .
git commit -m "Add new feature"

Push
git push origin feature/new-feature

На VDS
cd /opt/avito-assist-backend
git pull origin main
sudo systemctl restart avito-assist

text

---

## 🐛 Troubleshooting

### Сервис не запускается

sudo systemctl status avito-assist
sudo journalctl -u avito-assist -n 50

text

### Ошибки Perplexity API

Проверь:
- `PERPLEXITY_API_KEY` в `.env`
- Баланс на аккаунте Perplexity
- Логи: `tail -f logs/avito-assist.log`

### Вебхуки не приходят от Avito

1. Проверь настройки webhook в личном кабинете Avito
2. Убедись, что домен доступен: `curl https://your-domain.com/`
3. Проверь SSL: `curl https://your-domain.com/webhooks/avito`

---

## 📝 TODO / Roadmap

- [ ] Добавить enrichment данных об объявлении через Item API
- [ ] Реализовать UI для редактирования расписания
- [ ] Добавить мульти-аккаунтность (несколько проектов)
- [ ] Интеграция с CRM (webhook при создании лида)
- [ ] Dashboard с аналитикой и метриками
- [ ] Хранение истории диалогов
- [ ] A/B тестирование промптов
- [ ] Rate limiting для защиты от DDoS
- [ ] Docker-образ для упрощения деплоя

---

## 📄 Лицензия

MIT License

---

## 👤 Автор

**Твоё имя**
- GitHub: [@iradiomed33](https://github.com/iradiomed33)
- Email: your-email@example.com

---

## 🙏 Благодарности

- [Perplexity AI](https://www.perplexity.ai/) — за API
- [Avito](https://developers.avito.ru) — за Messenger API
- [FastAPI](https://fastapi.tiangolo.com/) — за фреймворк