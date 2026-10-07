#!/usr/bin/env python3
"""Комплексний верифікаційний тест для проєкту 'Агрегатор метеорологічних даних'.

Цей скрипт повністю перевіряє:
1. Бізнес-вимоги:
   - CLI-скрипт імпорту даних (ідемпотентність, збереження в БД).
   - GET /api/weather/average (середня темп., сума опадів, валідація дат).
   - GET /api/weather/extremes (дні з max і min температурами).
   - GET /api/weather/monthly/{year}/{month} (середня темп., масив днів з опадами).
2. Інженерні вимоги та Quality Gates:
   - Quality Gate 1: Агрегація на рівні БД (перевірка SQL AVG, MIN, MAX, SUM).
   - Quality Gate 2: Патерн Repository (ізоляція SQL-запитів у класі).
   - Quality Gate 3: Single Responsibility Principle (SRP) — клієнт API ізольований від БД.
   - Quality Gate 4: Docker & Docker Compose (конфігурація, зв'язок з Postgres і Redis).
   - Quality Gate 5: Кешування в Redis (перевірка X-Cache MISS -> HIT).
"""

import sys
import os
import inspect
from datetime import date, timedelta
import httpx

# Налаштування кодування для безпечного виводу у Windows консоль (cp1251)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Додаємо кореневу папку проєкту до шляхів
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.core.redis import get_redis_client
from app.core.cache import CacheService
from app.models.weather import WeatherData
from app.repositories.weather import WeatherAnalyticsRepository
from app.services.open_meteo import OpenMeteoClient
from app.services.weather_ingestion import WeatherIngestionService

# Базовий URL для тестування API
API_BASE_URL = f"http://localhost:{settings.APP_PORT}"

# Лічильники результатів
PASSED = 0
FAILED = 0


def log_test(name: str, passed: bool, detail: str = ""):
    global PASSED, FAILED
    status = "[PASS]" if passed else "[FAIL]"
    if passed:
        PASSED += 1
        print(f"  {status} {name}")
    else:
        FAILED += 1
        print(f"  {status} {name} -> Помилка: {detail}")


def test_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# =====================================================================
# 1. ТЕСТУВАННЯ ІНФРАСТРУКТУРИ ТА ПІДКЛЮЧЕНЬ
# =====================================================================
def test_infrastructure():
    test_section("1. Інфраструктура (PostgreSQL, Redis, Health Check)")

    # 1.1 Перевірка підключення до PostgreSQL
    try:
        db = SessionLocal()
        db.execute(WeatherData.__table__.select().limit(1))
        db.close()
        log_test("Підключення до PostgreSQL та доступність таблиці weather_data", True)
    except Exception as e:
        log_test("Підключення до PostgreSQL", False, str(e))

    # 1.2 Перевірка підключення до Redis
    try:
        r = get_redis_client()
        pong = r.ping()
        log_test("Підключення до Redis (PING/PONG)", pong is True)
    except Exception as e:
        log_test("Підключення до Redis", False, str(e))

    # 1.3 Перевірка API Health Check
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{API_BASE_URL}/health")
            data = resp.json()
            is_healthy = (
                resp.status_code == 200
                and data.get("database") == "connected"
                and data.get("cache") == "connected"
            )
            log_test("API /health статус (database=connected, cache=connected)", is_healthy, str(data))
    except Exception as e:
        log_test("API /health доступність", False, str(e))


# =====================================================================
# 2. ТЕСТУВАННЯ QUALITY GATES (АРХІТЕКТУРА ТА ЧИСТИЙ КОД)
# =====================================================================
def test_quality_gates():
    test_section("2. Перевірка Quality Gates (SRP, Repository, DB-Level Aggregation)")

    # 2.1 SRP (Single Responsibility Principle)
    # OpenMeteoClient не повинен залежати від БД чи імпортувати SQLAlchemy
    try:
        client_src = inspect.getsource(OpenMeteoClient)
        has_sql_import = (
            "sqlalchemy" in client_src.lower()
            or "session" in client_src.lower()
            or "weather_data" in client_src.lower()
        )
        log_test(
            "Quality Gate 3 (SRP): OpenMeteoClient ізольований від БД",
            not has_sql_import,
            "Клієнт містить прямі посилання на БД!"
        )
    except Exception as e:
        log_test("SRP аналіз OpenMeteoClient", False, str(e))

    # 2.2 Патерн Repository
    try:
        db = SessionLocal()
        repo = WeatherAnalyticsRepository(db)
        methods = ["save_bulk", "get_average_stats", "get_extremes", "get_monthly_stats"]
        has_methods = all(hasattr(repo, m) for m in methods)
        log_test(
            "Quality Gate 2 (Repository Pattern): WeatherAnalyticsRepository інкапсулює аналітику",
            has_methods,
            "Не всі методи реалізовані у репозиторії"
        )
        db.close()
    except Exception as e:
        log_test("Repository Pattern", False, str(e))

    # 2.3 Агрегація на рівні БД (Quality Gate 1)
    # Перевіряємо, що у згенерованих SQL-запитах репозиторію присутні SQL-функції
    try:
        db = SessionLocal()
        repo = WeatherAnalyticsRepository(db)

        # Перевірка get_average_stats (AVG, SUM, COUNT)
        avg_src = inspect.getsource(repo.get_average_stats)
        has_avg_sum = "func.avg" in avg_src and "func.sum" in avg_src

        # Перевірка get_extremes (MAX, MIN)
        extremes_src = inspect.getsource(repo.get_extremes)
        has_max_min = "func.max" in extremes_src and "func.min" in extremes_src

        # Перевірка get_monthly_stats (AVG, EXTRACT, filtering in SQL)
        monthly_src = inspect.getsource(repo.get_monthly_stats)
        has_monthly_sql = "func.avg" in monthly_src and "func.extract" in monthly_src

        all_sql_aggregated = has_avg_sum and has_max_min and has_monthly_sql
        log_test(
            "Quality Gate 1 (DB Aggregation): Розрахунки (AVG, SUM, MIN, MAX, EXTRACT) виконуються на стороні SQL",
            all_sql_aggregated,
            "Агрегаційні функції відсутні в коді репозиторію!"
        )
        db.close()
    except Exception as e:
        log_test("DB Aggregation перевірка", False, str(e))

    # 2.4 Стандарт SQLAlchemy 2.0 (Mapped, mapped_column) та відсутність дублювання індексів
    try:
        model_src = inspect.getsource(WeatherData)
        uses_mapped = "Mapped[" in model_src and "mapped_column(" in model_src
        log_test(
            "Стандарт SQLAlchemy 2.0: Використання Mapped та mapped_column у моделі WeatherData",
            uses_mapped,
            "Модель використовує застарілий синтаксис Column() замість Mapped/mapped_column"
        )

        # Перевірка на відсутність надлишкового дублюючого індексу idx_weather_city_date
        index_names = [idx.name for idx in WeatherData.__table__.indexes]
        has_redundant_index = "idx_weather_city_date" in index_names
        log_test(
            "Оптимізація БД: Відсутність дублюючого індексу поверх UniqueConstraint",
            not has_redundant_index,
            f"Знайдено зайвий дублюючий індекс: {index_names}"
        )
    except Exception as e:
        log_test("SQLAlchemy 2.0 / Index перевірка", False, str(e))

    # 2.5 Коректність обробки пропусків даних (не підставляти 0.0 при temp is None)
    try:
        open_meteo_src = inspect.getsource(OpenMeteoClient.fetch_historical_weather)
        skips_missing = "if temp is None:" in open_meteo_src and "continue" in open_meteo_src
        log_test(
            "Чистота даних: Пропуск днів з відсутніми замірами температури (без спотворення 0.0°C)",
            skips_missing,
            "Клієнт підставляє штучні нулі замість пропуску відсутніх даних"
        )
    except Exception as e:
        log_test("Перевірка пропусків даних", False, str(e))


# =====================================================================
# 3. ТЕСТУВАННЯ ІМПОРТУ ДАНИХ ТА ІДЕМПОТЕНТНОСТІ
# =====================================================================
def test_data_ingestion():
    test_section("3. Імпорт метеоданих та Ідемпотентність")

    db = SessionLocal()
    try:
        client = OpenMeteoClient()
        repo = WeatherAnalyticsRepository(db)
        cache = CacheService()
        service = WeatherIngestionService(client, repo, cache)

        # Тестовий діапазон дат
        end_d = date.today() - timedelta(days=2)
        start_d = end_d - timedelta(days=7)

        # Перший імпорт
        res1 = service.ingest_historical_data(
            city="Kosice",
            latitude=settings.DEFAULT_LATITUDE,
            longitude=settings.DEFAULT_LONGITUDE,
            start_date=start_d,
            end_date=end_d
        )
        count1 = res1["records_imported"]
        log_test(f"Імпорт метеоданих через WeatherIngestionService (записів: {count1})", count1 > 0)

        # Другий імпорт тих самих дат (перевірка ідемпотентності — ON CONFLICT DO UPDATE)
        res2 = service.ingest_historical_data(
            city="Kosice",
            latitude=settings.DEFAULT_LATITUDE,
            longitude=settings.DEFAULT_LONGITUDE,
            start_date=start_d,
            end_date=end_d
        )
        count2 = res2["records_imported"]
        log_test("Ідемпотентність збереження (повторний імпорт без дублювання)", count1 == count2)

    except Exception as e:
        log_test("Імпорт даних", False, str(e))
    finally:
        db.close()


# =====================================================================
# 4. ТЕСТУВАННЯ ЕНДПОІНТІВ API ТА БІЗНЕС-ВИМОГ
# =====================================================================
def test_api_endpoints():
    test_section("4. Бізнес-вимоги: Аналітичні ендпоінти API")

    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        # 4.1 GET /api/weather/average
        # 4.1.a Успішний запит
        end_d = date.today() - timedelta(days=2)
        start_d = end_d - timedelta(days=30)
        params = {
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "city": "Kosice"
        }
        resp = client.get("/api/weather/average", params=params)
        data = resp.json()
        valid_avg = (
            resp.status_code == 200
            and "average_temperature" in data
            and "total_precipitation" in data
            and data["records_count"] > 0
        )
        log_test(
            f"GET /api/weather/average (avg_temp={data.get('average_temperature')}, total_precip={data.get('total_precipitation')})",
            valid_avg,
            str(data)
        )

        # 4.1.b Валідація некоректного діапазону (start_date > end_date)
        bad_params = {
            "start_date": end_d.isoformat(),
            "end_date": start_d.isoformat()
        }
        bad_resp = client.get("/api/weather/average", params=bad_params)
        log_test(
            "GET /api/weather/average валідація дат (start_date > end_date повертає 400)",
            bad_resp.status_code == 400,
            f"Код відповіді: {bad_resp.status_code}"
        )

        # 4.2 GET /api/weather/extremes
        ext_resp = client.get("/api/weather/extremes", params={"city": "Kosice"})
        ext_data = ext_resp.json()
        max_t = ext_data.get("max_temperature")
        min_t = ext_data.get("min_temperature")
        valid_extremes = (
            ext_resp.status_code == 200
            and max_t is not None
            and min_t is not None
            and "date" in max_t
            and "temperature" in max_t
            and "date" in min_t
            and "temperature" in min_t
            and max_t["temperature"] >= min_t["temperature"]
        )
        log_test(
            f"GET /api/weather/extremes (Max: {max_t.get('date')} [{max_t.get('temperature')}°C], Min: {min_t.get('date')} [{min_t.get('temperature')}°C])",
            valid_extremes,
            str(ext_data)
        )

        # 4.3 GET /api/weather/monthly/{year}/{month}
        # 4.3.a Успішний запит
        target_year = start_d.year
        target_month = start_d.month
        month_resp = client.get(f"/api/weather/monthly/{target_year}/{target_month}?city=Kosice")
        m_data = month_resp.json()
        rainy_days = m_data.get("rainy_days", [])
        precip_days = m_data.get("days_with_precipitation", [])
        valid_monthly = (
            month_resp.status_code == 200
            and "average_temperature" in m_data
            and isinstance(rainy_days, list)
            and all(isinstance(d, int) and 1 <= d <= 31 for d in rainy_days)
            and rainy_days == precip_days
        )
        log_test(
            f"GET /api/weather/monthly/{target_year}/{target_month} (avg_temp={m_data.get('average_temperature')}, днів з опадами={len(rainy_days)})",
            valid_monthly,
            str(m_data)
        )

        # 4.3.b Валідація некоректного місяця (month > 12)
        bad_month_resp = client.get(f"/api/weather/monthly/{target_year}/13")
        log_test(
            "GET /api/weather/monthly валідація місяця (month=13 повертає 400)",
            bad_month_resp.status_code == 400,
            f"Код відповіді: {bad_month_resp.status_code}"
        )


# =====================================================================
# 5. ТЕСТУВАННЯ КЕШУВАННЯ В REDIS (QUALITY GATE 5)
# =====================================================================
def test_caching():
    test_section("5. Кешування в Redis (Quality Gate 5: X-Cache MISS -> HIT)")

    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
        cache = CacheService()

        # Очищаємо кеш перед тестом для гарантії холодного старту
        cache.clear_pattern("weather:*")

        end_d = date.today() - timedelta(days=2)
        start_d = end_d - timedelta(days=15)
        params = {
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "city": "Kosice"
        }

        # 1-й запит: кеш порожній -> повинен бути MISS
        resp1 = client.get("/api/weather/average", params=params)
        cache_header_1 = resp1.headers.get("X-Cache")

        # 2-й запит: результат вже у Redis -> повинен бути HIT
        resp2 = client.get("/api/weather/average", params=params)
        cache_header_2 = resp2.headers.get("X-Cache")

        is_caching_working = (
            cache_header_1 == "MISS"
            and cache_header_2 == "HIT"
            and resp1.json() == resp2.json()
        )

        log_test(
            f"Кешування /api/weather/average: Запит 1 = {cache_header_1}, Запит 2 = {cache_header_2}",
            is_caching_working,
            f"Отримано: header1={cache_header_1}, header2={cache_header_2}"
        )

        # Перевірка кешування для /api/weather/extremes
        cache.delete(f"weather:extremes:Kosice")
        ext_resp1 = client.get("/api/weather/extremes?city=Kosice")
        ext_resp2 = client.get("/api/weather/extremes?city=Kosice")
        ext_cached = (
            ext_resp1.headers.get("X-Cache") == "MISS"
            and ext_resp2.headers.get("X-Cache") == "HIT"
        )
        log_test(
            f"Кешування /api/weather/extremes: MISS ({ext_resp1.headers.get('X-Cache')}) -> HIT ({ext_resp2.headers.get('X-Cache')})",
            ext_cached
        )


# =====================================================================
# ТОЧКА ВХОДУ ТА ЗВІТ
# =====================================================================
def main():
    print("\n" + "#" * 70)
    print("  ЗАПУСК ПОВНОЇ ВЕРИФІКАЦІЇ: АГРЕГАТОР МЕТЕОРОЛОГІЧНИХ ДАНИХ")
    print("#" * 70)

    test_infrastructure()
    test_quality_gates()
    test_data_ingestion()
    test_api_endpoints()
    test_caching()

    print("\n" + "=" * 70)
    print(f"  РЕЗУЛЬТАТИ ВЕРИФІКАЦІЇ: ПРОЙДЕНО {PASSED}, НЕ ПРОЙДЕНО {FAILED}")
    print("=" * 70)

    if FAILED == 0:
        print("\n>>> ВСІ УМОВИ ЗАДАЧІ ТА QUALITY GATES УСПІШНО ВИКОНАНО! <<<\n")
        sys.exit(0)
    else:
        print(f"\n>>> УВАГА! Виявлено {FAILED} помилок під час тестування. <<<\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
