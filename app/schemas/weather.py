from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class WeatherAverageResponse(BaseModel):
    city: str
    start_date: date
    end_date: date
    average_temperature: Optional[float] = None
    total_precipitation: Optional[float] = None
    records_count: int = 0


class ExtremeDay(BaseModel):
    date: date
    temperature: float


class WeatherExtremesResponse(BaseModel):
    city: str
    max_temperature: Optional[ExtremeDay] = None
    min_temperature: Optional[ExtremeDay] = None


class WeatherMonthlyResponse(BaseModel):
    city: str
    year: int
    month: int
    average_temperature: Optional[float] = None
    rainy_days: List[int] = Field(default_factory=list)
    days_with_precipitation: List[int] = Field(default_factory=list)


class WeatherImportResponse(BaseModel):
    message: str
    city: str
    records_imported: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
