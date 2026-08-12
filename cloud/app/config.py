import os

if os.getenv("USE_PYDANTIC_SETTINGS"):
    try:
        from pydantic_settings import BaseSettings
    except ImportError:
        BaseSettings = object
else:
    BaseSettings = object


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/cloud_db.sqlite"
    )
    SKYOPS_ENV: str = os.getenv("SKYOPS_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    
    # Security & Auth Settings
    SKYOPS_AGENT_TOKEN: str = os.getenv("SKYOPS_AGENT_TOKEN", "")
    SKYOPS_INITIAL_ADMIN_PASSWORD: str = os.getenv("SKYOPS_INITIAL_ADMIN_PASSWORD", os.getenv("SKYOPS_ADMIN_PASSWORD", ""))
    SKYOPS_ADMIN_USERNAME: str = os.getenv("SKYOPS_ADMIN_USERNAME", "admin")
    SKYOPS_ADMIN_PASSWORD: str = os.getenv("SKYOPS_ADMIN_PASSWORD", "")
    SKYOPS_SECRET_KEY: str = os.getenv("SKYOPS_SECRET_KEY", "")
    SKYOPS_ALLOWED_ORIGINS: str = os.getenv(
        "SKYOPS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )


settings = Settings()
