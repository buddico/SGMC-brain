from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SGMC Brain"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5440/sgmc_brain"

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Cloudflare Access
    CF_ACCESS_REQUIRED: bool = False
    CF_ACCESS_TEAM_DOMAIN: str = ""
    CF_ACCESS_AUD: str = ""

    # Dev auth fallback
    DEV_AUTH_EMAIL: str = "dev@stroudgreenmedical.co.uk"
    DEV_AUTH_NAME: str = "Dev User"

    # SGMC Data Manager API (staff SSOT)
    STAFF_API_URL: str = "http://127.0.0.1:8080/api"

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Agent runtime
    AGENT_RUNTIME_URL: str = "http://127.0.0.1:8091"

    # File storage
    UPLOAD_DIR: str = "/data/uploads"
    POLICY_DIR: str = "/data/policies"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
