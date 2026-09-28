from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fixora API"
    environment: str = "development"
    database_url: str = "sqlite:///./fixora.db"
    jwt_secret: str = "change-me-in-production"
    jwt_expires_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    session_cookie_name: str = "fixora_access"
    csrf_cookie_name: str = "fixora_csrf"
    session_cookie_secure: bool = False
    session_cookie_domain: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    mpesa_env: str = "sandbox"
    mpesa_consumer_key: str | None = None
    mpesa_consumer_secret: str | None = None
    mpesa_shortcode: str | None = None
    mpesa_passkey: str | None = None
    mpesa_callback_url: str | None = None
    mpesa_callback_token: str | None = None

    media_root: str = "./media"
    storage_bucket: str | None = None
    storage_region: str | None = None
    storage_endpoint_url: str | None = None
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None
    storage_public_base_url: str | None = None
    max_upload_mb: int = 10

    platform_fee_percent: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def cors_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts.split(",") if x.strip()]


settings = Settings()
