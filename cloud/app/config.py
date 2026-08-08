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
        "DATABASE_URL", "postgresql://skyops:password@localhost:5432/skyops"
    )
    SKYOPS_ENV: str = os.getenv("SKYOPS_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
