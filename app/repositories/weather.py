from datetime import date
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, Integer
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.weather import WeatherData


class WeatherAnalyticsRepository:
    """Репозиторій для роботи з погодними даними та SQL-агрегаціями."""

    def __init__(self, db: Session):
        self.db = db

    def save_bulk(self, records: List[Dict[str, Any]]) -> int:
        if not records:
            return 0

        stmt = pg_insert(WeatherData).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_weather_city_date",
            set_={
                "temperature": stmt.excluded.temperature,
                "precipitation": stmt.excluded.precipitation
            }
        )
        self.db.execute(stmt)
        self.db.commit()
        return len(records)

    def get_average_stats(self, start_date: date, end_date: date, city: str) -> Dict[str, Any]:
        stmt = (
            select(
                func.avg(WeatherData.temperature).label("avg_temp"),
                func.sum(WeatherData.precipitation).label("total_precip"),
                func.count(WeatherData.id).label("count")
            )
            .where(
                WeatherData.city == city,
                WeatherData.date >= start_date,
                WeatherData.date <= end_date
            )
        )
        row = self.db.execute(stmt).first()
        if not row or row.count == 0 or row.avg_temp is None:
            return {
                "city": city,
                "start_date": start_date,
                "end_date": end_date,
                "average_temperature": None,
                "total_precipitation": None,
                "records_count": 0
            }

        return {
            "city": city,
            "start_date": start_date,
            "end_date": end_date,
            "average_temperature": round(float(row.avg_temp), 2),
            "total_precipitation": round(float(row.total_precip or 0.0), 2),
            "records_count": int(row.count)
        }

    def get_extremes(self, city: str) -> Dict[str, Any]:
        stmt_extremes = (
            select(
                func.max(WeatherData.temperature).label("max_temp"),
                func.min(WeatherData.temperature).label("min_temp")
            )
            .where(WeatherData.city == city)
        )
        row = self.db.execute(stmt_extremes).first()
        if not row or row.max_temp is None or row.min_temp is None:
            return {"city": city, "max_temperature": None, "min_temperature": None}

        max_day = self.db.execute(
            select(WeatherData.date, WeatherData.temperature)
            .where(WeatherData.city == city, WeatherData.temperature == row.max_temp)
            .order_by(WeatherData.date)
            .limit(1)
        ).first()

        min_day = self.db.execute(
            select(WeatherData.date, WeatherData.temperature)
            .where(WeatherData.city == city, WeatherData.temperature == row.min_temp)
            .order_by(WeatherData.date)
            .limit(1)
        ).first()

        return {
            "city": city,
            "max_temperature": {"date": max_day.date, "temperature": round(float(max_day.temperature), 2)} if max_day else None,
            "min_temperature": {"date": min_day.date, "temperature": round(float(min_day.temperature), 2)} if min_day else None
        }

    def get_monthly_stats(self, year: int, month: int, city: str) -> Dict[str, Any]:
        stmt_avg = (
            select(func.avg(WeatherData.temperature).label("avg_temp"), func.count(WeatherData.id).label("count"))
            .where(
                WeatherData.city == city,
                func.extract("year", WeatherData.date) == year,
                func.extract("month", WeatherData.date) == month
            )
        )
        avg_row = self.db.execute(stmt_avg).first()

        stmt_rainy = (
            select(func.cast(func.extract("day", WeatherData.date), Integer))
            .where(
                WeatherData.city == city,
                func.extract("year", WeatherData.date) == year,
                func.extract("month", WeatherData.date) == month,
                WeatherData.precipitation > 0
            )
            .order_by(WeatherData.date)
        )
        rainy_days = [int(r[0]) for r in self.db.execute(stmt_rainy).all()]

        avg_temp = round(float(avg_row.avg_temp), 2) if avg_row and avg_row.count > 0 and avg_row.avg_temp is not None else None

        return {
            "city": city,
            "year": year,
            "month": month,
            "average_temperature": avg_temp,
            "rainy_days": rainy_days,
            "days_with_precipitation": rainy_days
        }


WeatherRepository = WeatherAnalyticsRepository
