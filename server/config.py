from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

    # HTTP client
    request_timeout: float = 15.0
    bot_test_timeout: float = 10.0
    max_redirects: int = 5

    # User agents
    browser_ua: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    # Analysis
    result_cache_ttl: int = 3600  # 1 hour

    # External services
    resend_api_key: str = ""
    google_sheets_credentials: str = ""  # path to service account JSON
    google_sheets_id: str = ""

    model_config = {"env_prefix": "AIC_"}


settings = Settings()
