from datetime import date
from typing import Dict, Any, List, Optional

from app.services.open_meteo import OpenMeteoClient
from app.repositories.weather import WeatherAnalyticsRepository
from app.core.cache import CacheService


class WeatherIngestionService:
    """Сервіс для збереження погодних даних у БД та інвалідації кешу."""

    def __init__(
        self,
        api_client: OpenMeteoClient,
        repository: WeatherAnalyticsRepository,
        cache_service: Optional[CacheService] = None
    ):
        self.api_client = api_client
        self.repository = repository
        self.cache_service = cache_service

    def ingest_historical_data(
        self,
        city: str,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        raw_records = self.api_client.fetch_historical_weather(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date
        )

        db_records: List[Dict[str, Any]] = [
            {
                "city": city,
                "date": item["date"],
                "temperature": item["temperature"],
                "precipitation": item["precipitation"]
            }
            for item in raw_records
        ]

        saved_count = self.repository.save_bulk(db_records)

        if self.cache_service:
            self.cache_service.clear_pattern("weather:*")

        return {
            "city": city,
            "records_imported": saved_count,
            "start_date": start_date,
            "end_date": end_date
        }


# Аліас
WeatherService = WeatherIngestionService
