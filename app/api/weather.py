from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.config import settings
from app.core.cache import CacheService, get_cache_service
from app.api.dependencies import (
    get_weather_repository,
    get_weather_ingestion_service,
)
from app.repositories.weather import WeatherAnalyticsRepository
from app.services.weather_ingestion import WeatherIngestionService
from app.schemas.weather import (
    WeatherAverageResponse,
    WeatherExtremesResponse,
    WeatherMonthlyResponse,
    WeatherImportResponse,
)

router = APIRouter()


@router.get("/average", response_model=WeatherAverageResponse)
def get_average_weather(
    response: Response,
    start_date: date = Query(..., description="Початкова дата (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Кінцева дата (YYYY-MM-DD)"),
    city: Optional[str] = Query(None),
    repo: WeatherAnalyticsRepository = Depends(get_weather_repository),
    cache: CacheService = Depends(get_cache_service),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date не може бути більшою за end_date"
        )

    target_city = city or settings.DEFAULT_CITY
    cache_key = f"weather:average:{target_city}:{start_date}:{end_date}"

    cached = cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    data = repo.get_average_stats(start_date, end_date, target_city)
    cache.set(cache_key, data)
    response.headers["X-Cache"] = "MISS"
    return data


@router.get("/extremes", response_model=WeatherExtremesResponse)
def get_temperature_extremes(
    response: Response,
    city: Optional[str] = Query(None),
    repo: WeatherAnalyticsRepository = Depends(get_weather_repository),
    cache: CacheService = Depends(get_cache_service),
):
    target_city = city or settings.DEFAULT_CITY
    cache_key = f"weather:extremes:{target_city}"

    cached = cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    data = repo.get_extremes(target_city)
    cache.set(cache_key, data)
    response.headers["X-Cache"] = "MISS"
    return data


@router.get("/monthly/{year}/{month}", response_model=WeatherMonthlyResponse)
def get_monthly_weather(
    response: Response,
    year: int,
    month: int,
    city: Optional[str] = Query(None),
    repo: WeatherAnalyticsRepository = Depends(get_weather_repository),
    cache: CacheService = Depends(get_cache_service),
):
    if not (1 <= month <= 12):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер місяця (month) повинен бути в діапазоні від 1 до 12"
        )
    if year < 1900 or year > 2100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вказано некоректний рік"
        )

    target_city = city or settings.DEFAULT_CITY
    cache_key = f"weather:monthly:{target_city}:{year}:{month}"

    cached = cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    data = repo.get_monthly_stats(year, month, target_city)
    cache.set(cache_key, data)
    response.headers["X-Cache"] = "MISS"
    return data


@router.post("/import", response_model=WeatherImportResponse, status_code=status.HTTP_201_CREATED)
def trigger_import(
    city: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    days: int = Query(365, ge=1, le=1000),
    service: WeatherIngestionService = Depends(get_weather_ingestion_service),
):
    target_city = city or settings.DEFAULT_CITY
    lat = latitude if latitude is not None else settings.DEFAULT_LAT
    lon = longitude if longitude is not None else settings.DEFAULT_LON

    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=days)

    try:
        res = service.ingest_historical_data(target_city, lat, lon, start_date, end_date)
        return {
            "message": f"Імпортовано дані для {target_city}",
            "city": target_city,
            "records_imported": res["records_imported"],
            "start_date": start_date,
            "end_date": end_date,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка імпорту: {str(e)}"
        )
