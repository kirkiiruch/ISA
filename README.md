# Агрегатор метеорологічних даних (Weather Analytics API)

Сервіс для імпорту та агрегації історичних погодних даних з відкритого API **Open-Meteo**, збереження їх у **PostgreSQL**, кешування аналітичних запитів у **Redis** та надання REST API для аналітичних зрізів.

---

## 🛠 Технологічний стек

* **Мова та фреймворк:** Python 3.11 / 3.14, FastAPI
* **База даних та ORM:** PostgreSQL 16, SQLAlchemy 2.0 (psycopg2-binary)
* **Кешування:** Redis 7
* **HTTP-клієнт:** HTTPX
* **Валідація та DTO:** Pydantic v2
* **Контейнеризація:** Docker, Docker Compose

---

## 🏛 Архітектура та Quality Gates

1. **Агрегація на рівні БД (Quality Gate 1):**
   * Усі обчислення (`AVG`, `SUM`, `MIN`, `MAX`, фільтрація за `EXTRACT`) виконуються виключно ядром PostgreSQL через функції SQLAlchemy (`func.avg()`, `func.sum()`, `func.max()`, `func.min()`).
   * Масив усіх записів не вивантажується в пам'ять додатку.
2. **Патерн Repository (Quality Gate 2):**
   * Складні SQL-запити та бізнес-агрегації інкапсульовані в класі `WeatherAnalyticsRepository` (`app/repositories/weather.py`).
3. **Single Responsibility Principle (SRP) (Quality Gate 3):**
   * `OpenMeteoClient` (`app/services/open_meteo.py`) відповідає виключно за мережеві HTTP-запити до зовнішнього API Open-Meteo і не має жодних знань про базу даних.
   * Збереженням даних та координацією займається окремий сервіс `WeatherIngestionService` (`app/services/weather_ingestion.py`).
4. **Кешування в Redis (Quality Gate 5):**
   * Важкі агрегаційні запити кешуються в Redis за унікальними ключами параметрів.
   * Перший запит повертає заголовок `X-Cache: MISS` та записує результат у Redis.
   * Наступні запити повертають `X-Cache: HIT` безпосередньо з пам'яті Redis.
   * При імпорті нових даних кеш автоматично інвалідується.
5. **Docker & Docker Compose (Quality Gate 4):**
   * Автоматичне розгортання всього оточення (FastAPI + PostgreSQL + Redis) за допомогою однієї команди `docker compose up -d`.
   * Створення таблиць БД відбувається автоматично при старті API через Lifespan.

---

## 🚀 Швидкий запуск

### 1. Запуск через Docker Compose
```bash
docker compose up -d --build
```

### 2. Імпорт погодних даних (CLI)
Стягує історичні дані за останній рік (365 днів) для вибраного міста (за замовчуванням Кошице):
```bash
# Всередині Docker контейнера:
docker compose exec api python scripts/import_weather.py --days 365

# Або на хості (через venv):
python scripts/import_weather.py --days 365
```

Параметри CLI:
* `--city` — назва міста (наприклад: `--city Kosice`)
* `--lat` — широта (наприклад: `--lat 48.7164`)
* `--lon` — довгота (наприклад: `--lon 21.2611`)
* `--days` — кількість днів вглиб (за замовчуванням 365)
* `--start-date` / `--end-date` — конкретні дати (формат `YYYY-MM-DD`)

---

## 📡 Специфікація API (Endpoints)

| Метод | Шлях | Опис |
| :--- | :--- | :--- |
| **GET** | `/api/weather/average` | Середня температура та сума опадів за період (`?start_date=...&end_date=...`) |
| **GET** | `/api/weather/extremes` | Дні з максимальною та мінімальною температурою за весь час |
| **GET** | `/api/weather/monthly/{year}/{month}` | Середня температура та масив чисел днів з опадами за місяць |
| **POST** | `/api/weather/import` | Ендпоінт для запуску імпорту метеоданих |
| **GET** | `/health` | Перевірка з'єднання з PostgreSQL та Redis |
| **GET** | `/docs` | Інтерактивна документація Swagger UI |

---

## 🧪 Запуск тестів (test.py)

Скрипт перевіряє всі 18 критеріїв якості, бізнес-вимог та Quality Gates:
```bash
# Запуск у Docker контейнері:
docker compose exec api python test.py

# Або на локальній машині:
python test.py
```
