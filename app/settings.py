from pydantic_settings import BaseSettings, SettingsConfigDict


from pydantic_settings import BaseSettings, SettingsConfigDict


class AvitoSettings(BaseSettings):
    """
    Настройки для интеграции с Avito API и OAuth2.

    Значения читаются из переменных окружения или .env (если он есть).
    Для dev/тестов заданы безопасные значения по умолчанию (DUMMY),
    которые нужно заменить реальными перед подключением к боевому Авито.
    """

    avito_client_id: str = "DUMMY_CLIENT_ID"
    avito_client_secret: str = "DUMMY_CLIENT_SECRET"
    avito_redirect_uri: str = "http://localhost:8000/avito/oauth/callback"

    avito_api_base_url: str = "https://api.avito.ru"
    avito_auth_base_url: str = "https://api.avito.ru"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Тестовый access_token для одного аккаунта Авито (MVP / dev).
    # В будущем будет заменён на хранилище токенов из OAuth.
    avito_test_access_token: str = "DUMMY_AVITO_TEST_ACCESS_TOKEN"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")



class AppSettings(BaseSettings):
    """
    Общие настройки приложения (на будущее).
    """

    app_name: str = "Avito Assist Backend"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


avito_settings = AvitoSettings()
app_settings = AppSettings()
