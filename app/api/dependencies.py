from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.cache import CacheService, get_cache_service
from app.repositories.weather import WeatherAnalyticsRepository
from app.services.open_meteo import OpenMeteoClient
from app.services.weather_ingestion import WeatherIngestionService


def get_weather_repository(
    db: Session = Depends(get_db)
) -> WeatherAnalyticsRepository:
    """Dependency для отримання WeatherAnalyticsRepository."""
    return WeatherAnalyticsRepository(db)


def get_open_meteo_client() -> OpenMeteoClient:
    """Dependency для отримання клієнта Open-Meteo."""
    return OpenMeteoClient()


def get_weather_ingestion_service(
    client: OpenMeteoClient = Depends(get_open_meteo_client),
    repository: WeatherAnalyticsRepository = Depends(get_weather_repository),
    cache_service: CacheService = Depends(get_cache_service)
) -> WeatherIngestionService:
    """Dependency для отримання WeatherIngestionService."""
    return WeatherIngestionService(
        api_client=client,
        repository=repository,
        cache_service=cache_service
    )
