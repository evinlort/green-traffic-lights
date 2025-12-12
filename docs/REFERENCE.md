# API and Component Reference / Справочник API и компонентов

This document lists all public APIs, functions, and client components available in the project. Each section contains English and Russian descriptions, plus examples and usage guidance.

## Flask application (`app.py`)

### English
- **`app`** – Flask application configured with:
  - `static_folder="static"`, `static_url_path=""` to serve the PWA assets.
  - `SQLALCHEMY_DATABASE_URI` – pulled from `DATABASE_URL` or defaults to `sqlite:///greenlights.db` in the repo root.
  - `SQLALCHEMY_TRACK_MODIFICATIONS=False`.
- The application registers the routes blueprint from `routes.py` and initializes the database via `init_db`.
- **Running:** `flask --app app run --host 0.0.0.0 --port 8000` or `gunicorn --bind 0.0.0.0:8000 app:app`.

### Русский
- **`app`** – приложение Flask, сконфигурированное следующим образом:
  - `static_folder="static"`, `static_url_path=""` для отдачи PWA-ресурсов.
  - `SQLALCHEMY_DATABASE_URI` – из переменной `DATABASE_URL` или по умолчанию `sqlite:///greenlights.db` в корне репозитория.
  - `SQLALCHEMY_TRACK_MODIFICATIONS=False`.
- Приложение регистрирует blueprint маршрутов из `routes.py` и инициализирует базу через `init_db`.
- **Запуск:** `flask --app app run --host 0.0.0.0 --port 8000` или `gunicorn --bind 0.0.0.0:8000 app:app`.

## Database helper (`db.py`)

### English
- **`db`** – a shared `SQLAlchemy` instance used by models.
- **`init_db(app: Flask) -> None`** – initialize the extension and create tables inside the application context.
- **Usage example:**
  ```python
  from flask import Flask
  from db import init_db

  app = Flask(__name__)
  app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"
  init_db(app)
  ```

### Русский
- **`db`** – общий экземпляр `SQLAlchemy`, используемый моделями.
- **`init_db(app: Flask) -> None`** – инициализирует расширение и создаёт таблицы в контексте приложения.
- **Пример использования:**
  ```python
  from flask import Flask
  from db import init_db

  app = Flask(__name__)
  app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local.db"
  init_db(app)
  ```

## Data model (`models/click_event.py`)

### English
- **`ClickEvent`** – SQLAlchemy model representing a click report:
  - `id` (int, PK, autoincrement)
  - `lat`, `lon` (float, required) – geographic coordinates.
  - `speed` (float, optional) – speed in km/h if available.
  - `timestamp` (datetime, timezone-aware, required) – when the click happened.
  - `created_at` (datetime, timezone-aware, default `func.now()`) – server insert time.
- Records are created by `save_click_to_db` inside `routes.py`.

### Русский
- **`ClickEvent`** – модель SQLAlchemy, описывающая отправку клика:
  - `id` (int, PK, autoincrement)
  - `lat`, `lon` (float, обязательные) – координаты.
  - `speed` (float, опционально) – скорость в км/ч, если доступна.
  - `timestamp` (datetime с таймзоной, обязательное) – момент клика.
  - `created_at` (datetime с таймзоной, по умолчанию `func.now()`) – время вставки на сервере.
- Записи создаются функцией `save_click_to_db` из `routes.py`.

## Traffic light service (`services/traffic_lights.py`)

### English
- **Purpose:** Validate how far a click is from known traffic lights.
- **Configuration:**
  - `TRAFFIC_LIGHTS_FILE` – path to a JSON list of `{ "lat": number, "lon": number }` entries. Relative paths resolve from `current_app.root_path`. Defaults to `light_traffics.json`.
- `TRAFFIC_LIGHT_MAX_DISTANCE_METERS` – maximum allowed distance in meters (default `50.0`). Non‑finite or negative values fall back to the default.
- **Public function:**
  - `validate_click_distance(lat: float, lon: float) -> Optional[Tuple[dict, int]]`
    - Loads and caches the traffic lights list (with mtime-based reloads).
    - Computes the haversine distance to the nearest light.
    - Returns `None` when the click is allowed; otherwise returns `(payload, status_code)` with a localized error message and `distance_m` detail.
- **Usage example:**
  ```python
  from services.traffic_lights import validate_click_distance

  lat, lon = 55.75, 37.61
  validation = validate_click_distance(lat, lon)
  if validation:
      payload, status = validation
      # Handle the 400 response
  else:
      # Proceed to persist the click
  ```

### Русский
- **Назначение:** Проверять расстояние клика до ближайшего светофора.
- **Конфигурация:**
  - `TRAFFIC_LIGHTS_FILE` – путь к JSON-списку объектов `{ "lat": number, "lon": number }`. Относительные пути считаются от `current_app.root_path`. По умолчанию `light_traffics.json`.
- `TRAFFIC_LIGHT_MAX_DISTANCE_METERS` – максимально допустимое расстояние в метрах (по умолчанию `50.0`). Не‑числовые или отрицательные значения заменяются дефолтом.
- **Публичная функция:**
  - `validate_click_distance(lat: float, lon: float) -> Optional[Tuple[dict, int]]`
    - Загружает и кеширует список светофоров (перечитывает при изменении mtime).
    - Считает расстояние по формуле гаверсина до ближайшего светофора.
    - Возвращает `None`, если клик разрешён; иначе `(payload, status_code)` с локализованным текстом ошибки и полем `distance_m`.
- **Пример использования:**
  ```python
  from services.traffic_lights import validate_click_distance

  lat, lon = 55.75, 37.61
  validation = validate_click_distance(lat, lon)
  if validation:
      payload, status = validation
      # Обработать ответ 400
  else:
      # Продолжить сохранение клика
  ```

## Routes (`routes.py`)

### English
- **Blueprint `bp`** – mounted at root.
- **`index()`** – `GET /` serves `static/index.html` from the configured static folder.
- **`api_click()`** – `POST /api/click` accepts geolocation payloads and persists them.
  - **Request JSON:**
    ```json
    {
      "lat": 55.75,
      "lon": 37.61,
      "speed": 42.3,        // optional, km/h
      "timestamp": "2024-01-01T12:00:00Z"
    }
    ```
  - **Validation:**
    - Ensures numeric `lat`/`lon`, optional numeric `speed`, ISO 8601 `timestamp` with timezone.
    - Calls `validate_click_distance`; if the click is too far, returns 400 with `{ "error": <message>, "details": {"distance_m": <float>} }`.
  - **Responses:**
    - `200 OK` with `{ "status": "ok" }` on success.
    - `400 Bad Request` for missing/invalid fields or excessive distance.
  - **Example request:**
    ```bash
    curl -X POST http://localhost:8000/api/click \
      -H "Content-Type: application/json" \
      -d '{"lat":55.75,"lon":37.61,"timestamp":"2024-01-01T12:00:00Z"}'
    ```
- **Helper:** `save_click_to_db(lat, lon, speed, timestamp)` – creates and commits a `ClickEvent` record.

### Русский
- **Blueprint `bp`** – подключён к корню.
- **`index()`** – `GET /` отдаёт `static/index.html` из настроенной статической папки.
- **`api_click()`** – `POST /api/click` принимает геоданные и сохраняет их.
  - **Тело запроса (JSON):**
    ```json
    {
      "lat": 55.75,
      "lon": 37.61,
      "speed": 42.3,        // опционально, км/ч
      "timestamp": "2024-01-01T12:00:00Z"
    }
    ```
  - **Валидация:**
    - Проверка числовых `lat`/`lon`, опциональной числовой `speed`, ISO 8601 `timestamp` с таймзоной.
    - Вызов `validate_click_distance`; при большом расстоянии возвращает 400 с `{ "error": <текст>, "details": {"distance_m": <float>} }`.
  - **Ответы:**
    - `200 OK` с `{ "status": "ok" }` при успехе.
    - `400 Bad Request` при отсутствии/ошибке полей или превышении дистанции.
  - **Пример запроса:**
    ```bash
    curl -X POST http://localhost:8000/api/click \
      -H "Content-Type: application/json" \
      -d '{"lat":55.75,"lon":37.61,"timestamp":"2024-01-01T12:00:00Z"}'
    ```
- **Вспомогательная функция:** `save_click_to_db(lat, lon, speed, timestamp)` – создаёт и фиксирует запись `ClickEvent`.

## Front-end components (`static/`)

### English
- **`index.html`** – Russian-language PWA shell with:
  - Title `Зелёный Светофор`.
  - Primary action button `#go-button` labeled "Поехали".
  - Status paragraph `#status` for live updates.
- **`styles.css`** – styles for a centered layout and the stateful circular action button. Modifier classes (`go-button--requesting`, `--sending`, `--success`, `--error`) provide visual feedback.
- **`main.js`** – client logic:
  - Reads `#go-button` and `#status` elements.
  - Registers a service worker from `/service-worker.js` on window load.
  - On click, requests geolocation with high accuracy and 10s timeout; converts speed to km/h if available.
  - Sends payload via `fetch('/api/click')`; displays success or error messages in Russian and toggles button state classes.
- **Usage:** Open `http://localhost:8000/` and press the button to submit your current position. Ensure geolocation permissions are granted.

### Русский
- **`index.html`** – оболочка PWA на русском языке:
  - Заголовок `Зелёный Светофор`.
  - Основная кнопка действия `#go-button` с текстом «Поехали».
  - Абзац состояния `#status` для живых обновлений.
- **`styles.css`** – стили центрированного интерфейса и круглой кнопки с модификаторами состояний (`go-button--requesting`, `--sending`, `--success`, `--error`).
- **`main.js`** – клиентская логика:
  - Находит элементы `#go-button` и `#status`.
  - Регистрирует service worker из `/service-worker.js` при загрузке окна.
  - По клику запрашивает геолокацию с высокой точностью и таймаутом 10 секунд; переводит скорость в км/ч при наличии.
  - Отправляет данные через `fetch('/api/click')`; выводит сообщения об успехе или ошибке и переключает модификаторы кнопки.
- **Использование:** Откройте `http://localhost:8000/` и нажмите кнопку, чтобы отправить текущие координаты. Убедитесь, что разрешён доступ к геолокации.

## Configuration recap / Итоги по настройкам
- `DATABASE_URL` – overrides the database URI (e.g., to a PostgreSQL URL) instead of the default SQLite file.
- `TRAFFIC_LIGHTS_FILE` – custom path to the traffic lights JSON.
- `TRAFFIC_LIGHT_MAX_DISTANCE_METERS` – distance threshold for `validate_click_distance`.

## Development tips / Советы по разработке
- Use `pip install -r requirements.txt` to install dependencies.
- To inspect stored clicks, open a Python shell inside `flask shell` and query `ClickEvent.query.all()`.
- To update traffic lights data, edit the JSON file referenced by `TRAFFIC_LIGHTS_FILE`; reloads happen automatically when the mtime changes.

