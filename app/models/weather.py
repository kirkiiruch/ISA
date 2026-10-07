from datetime import date, datetime
from sqlalchemy import String, Float, Date, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String(100), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    temperature: Mapped[float] = mapped_column(Float)
    precipitation: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("city", "date", name="uq_weather_city_date"),
    )
