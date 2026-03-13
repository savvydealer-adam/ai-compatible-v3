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

    # JWT
    jwt_secret: str = ""
    jwt_expiry_days: int = 30

    # External services
    resend_api_key: str = ""
    google_sheets_credentials: str = ""  # path to service account JSON
    google_sheets_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    google_oauth_client_id: str = ""

    # AI Live Verification (optional)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    kimi_api_key: str = ""
    perplexity_api_key: str = ""
    cohere_api_key: str = ""
    ai_verify_enabled: bool = False
    ai_verify_timeout: float = 60.0
    playwright_timeout: float = 20.0

    # Database (Cloud SQL via asyncpg)
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = ""
    database_user: str = "postgres"
    database_password: str = ""
    database_unix_socket: str = ""  # Cloud SQL socket path

    model_config = {"env_prefix": "AIC_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
