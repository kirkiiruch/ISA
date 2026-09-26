# Recipe Management REST API

Сучасний асинхронний REST API для управління каталогом кулінарних рецептів та інгредієнтів. Сервіс спроєктовано з дотриманням принципів **багатошарової архітектури (Onion / Layered Architecture)**, суворої типізації даних та повної контейнеризації робочого середовища.

---

## Технологічний стек

* **Фреймворк:** FastAPI (Python 3.11+)
* **ORM & База даних:** SQLAlchemy 2.0, PostgreSQL 15, драйвер `psycopg2-binary`
* **Валідація та DTO:** Pydantic v2
* **Контейнеризація та оркестрація:** Docker, Docker Compose
* **Сервер застосунку:** Uvicorn (Lifespan Context Manager)

---

## Архітектурний дизайн (Onion Architecture)

Проєкт розділено на незалежні шари, де кожен модуль відповідає строго за свою зону відповідальності (Separation of Concerns):

```text
docker-base/
├── app/
│   ├── api/                  # Presentation Layer (HTTP-контролери та DI)
│   │   ├── dependencies.py   # Фабрики впровадження залежностей (Depends)
│   │   └── recipes.py        # Роутери, HTTP-статуси та обробка помилок
│   ├── core/                 # Core Layer (Конфігурація та інфраструктура)
│   │   └── database.py       # Engine, DeclarativeBase, фабрика сесій
│   ├── models/               # Data Persistence Layer (ORM-моделі SQLAlchemy)
│   │   └── recipe.py         # Моделі Recipe та Ingredient, каскадні зв'язки
│   ├── repositories/         # Data Access Layer (Паттерн Репозиторій)
│   │   └── recipe_repo.py    # Побудова SQL-запитів, фільтрація, selectinload
│   ├── schemas/              # Business Validation Layer (Pydantic DTOs)
│   │   └── recipe.py         # Схеми RecipeCreate, RecipeUpdate, RecipeResponse
│   └── main.py               # Точка входу, керування життєвим циклом (lifespan)
├── docker-compose.yml        # Оркестрація сервісів (API, Postgres, Redis)
├── Dockerfile                # Опис складання образу API-сервісу
├── requirements.txt          # Фіксація залежностей проєкту
└── .env                      # Конфігурація змінних середовища
```

---

## Специфікація API (Endpoints)

| Метод | Шлях | Статус-код | Опис |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/recipes` | `201 Created` | Створення нового рецепта та списку його інгредієнтів |
| **GET** | `/api/recipes` | `200 OK` | Отримання каталогу з фільтрами за часом та інгредієнтами |
| **GET** | `/api/v1/recipes/{id}` | `200 OK` / `404` | Отримання повної інформації про конкретний рецепт |
| **PATCH** | `/api/v1/recipes/{id}` | `200 OK` / `404` | Часткове оновлення полів страви або списку інгредієнтів |
| **DELETE** | `/api/v1/recipes/{id}` | `204 No Content` | Видалення рецепта з каскадним очищенням інгредієнтів |
| **GET** | `/` | `200 OK` | Системний health check та перевірка готовності сервісу |

---

## Інженерні особливості реалізації

1. **Цілісність даних та Cascade Delete:**
   * Зв'язок One-to-Many між рецептом та інгредієнтами захищено на рівні бази (`ondelete="CASCADE"`) та на рівні ORM (`cascade="all, delete-orphan"`). При видаленні рецепта пов'язані інгредієнти гарантовано видаляються з таблиці `ingredients`.
2. **Оптимізація запитів (Проблема N+1):**
   * Вибірка зв'язаних сутностей здійснюється через стратегію випереджального завантаження `selectinload`, яка виконує оптимізовані запити замість десятків окремих звернень до бази.
3. **Регістронезалежний пошук:**
   * Фільтрація за назвою інгредієнта реалізована через `Recipe.ingredients.any(Ingredient.name.ilike(f"%{clean}%"))`, що дозволяє знаходити страви незалежно від регістру символів.
4. **Сувора валідація вхідних даних (DTO):**
   * Валідатори Pydantic v2 автоматично проводять санітизацію рядків (`.strip()`), відсікають порожні значення та контролюють бізнес-обмеження (`prep_time_minutes > 0`).

---

## Інструкція зі швидкого запуску

### 1. Клонування репозиторію
```powershell
git clone <URL_ВАШОГО_РЕПОЗИТОРІЮ>
cd docker-base
```

### 2. Конфігурація середовища
Створіть файл `.env` у кореневій директорії проєкту:
```env
APP_PORT=8000
POSTGRES_USER=app_user
POSTGRES_PASSWORD=supersecretpassword
POSTGRES_DB=app_db
POSTGRES_PORT=5432
POSTGRES_HOST=db
REDIS_PORT=6379
```

### 3. Збірка та запуск у Docker
```powershell
# Запуск контейнерів у фоновому режимі зі збіркою образу
docker compose up -d --build

# Перегляд логів запуску API
docker compose logs -f api
```

Сервер буде доступний за адресою: `http://localhost:8000`.

---

## Документація та тестування

Після запуску контейнерів інтерактивна документація доступна за адресами:

* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Керування життєвим циклом контейнерів

* **Зупинка зі збереженням даних у базі:**
  ```powershell
  docker compose down
  ```
* **Повне очищення середовища (разом із базою даних):**
  ```powershell
  docker compose down -v
  ```