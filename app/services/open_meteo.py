from datetime import date
from typing import List, Dict, Any
import httpx


class OpenMeteoClient:
    """HTTP-клієнт для завантаження погоди з відкритого API Open-Meteo."""

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def fetch_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ["temperature_2m_mean", "precipitation_sum"],
            "timezone": "auto"
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.ARCHIVE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("daily", {})
        times = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        precips = daily.get("precipitation_sum", [])

        records: List[Dict[str, Any]] = []
        for d_str, temp, precip in zip(times, temps, precips):
            # Пропускаємо дні без вимірювань, щоб не підставляти штучні нулі
            if temp is None:
                continue

            records.append({
                "date": date.fromisoformat(d_str),
                "temperature": round(float(temp), 2),
                "precipitation": round(float(precip or 0.0), 2)
            })

        return records
