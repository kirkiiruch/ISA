import os
import sys
import argparse
from datetime import date, timedelta

# Додаємо корінь проєкту в sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.cache import CacheService
from app.repositories.weather import WeatherAnalyticsRepository
from app.services.open_meteo import OpenMeteoClient
from app.services.weather_ingestion import WeatherIngestionService


def main():
    parser = argparse.ArgumentParser(description="Імпорт історичних метеоданих за останній рік")
    parser.add_argument("--city", default=settings.DEFAULT_CITY, help="Назва міста")
    parser.add_argument("--lat", type=float, default=settings.DEFAULT_LAT, help="Широта")
    parser.add_argument("--lon", type=float, default=settings.DEFAULT_LON, help="Довгота")
    parser.add_argument("--days", type=int, default=365, help="Кількість днів вглиб (за замовчуванням 365)")
    args = parser.parse_args()

    # Дані в архіві Open-Meteo зазвичай доступні до позавчора
    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=args.days)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        service = WeatherIngestionService(
            api_client=OpenMeteoClient(),
            repository=WeatherAnalyticsRepository(db),
            cache_service=CacheService()
        )

        result = service.ingest_historical_data(
            city=args.city,
            latitude=args.lat,
            longitude=args.lon,
            start_date=start_date,
            end_date=end_date
        )

        print(f"Успішно імпортовано {result['records_imported']} днів погоди для {args.city} (з {start_date} по {end_date})")

    finally:
        db.close()


if __name__ == "__main__":
    main()
