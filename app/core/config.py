import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "weather_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_HOST: str = "db"

    REDIS_HOST: str = "cache"
    REDIS_PORT: int = 6379
    CACHE_EXPIRE: int = 3600

    DEFAULT_CITY: str = "Kosice"
    DEFAULT_LAT: float = 48.7164
    DEFAULT_LON: float = 21.2611
    APP_PORT: int = 8000

    @property
    def DEFAULT_CITY_NAME(self) -> str:
        return self.DEFAULT_CITY

    @property
    def DEFAULT_LATITUDE(self) -> float:
        return self.DEFAULT_LAT

    @property
    def DEFAULT_LONGITUDE(self) -> float:
        return self.DEFAULT_LON

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def db_host(self) -> str:
        # Автоматичне перемикання на localhost при запуску тестів/скриптів на хості
        if not os.path.exists("/.dockerenv") and self.POSTGRES_HOST in ("db", "postgres_db"):
            return "localhost"
        return self.POSTGRES_HOST

    @property
    def redis_host(self) -> str:
        if not os.path.exists("/.dockerenv") and self.REDIS_HOST in ("cache", "redis", "redis_cache"):
            return "localhost"
        return self.REDIS_HOST

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.db_host}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
