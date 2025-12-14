# API and Component Reference / Справочник API и компонентов

This document lists all public APIs, functions, and client components available in the project. Each section contains English and Russian descriptions, plus examples and usage guidance.

## Flask application (`app.py` and `green_traffic_lights/__init__.py`)

### English
- **`create_app()`** – factory that configures the Flask app with:
  - `static_folder` pointing at the project `static/` directory and `static_url_path=""` to serve the PWA assets from root.
  - Settings from `green_traffic_lights.config.Config`, including `SQLALCHEMY_DATABASE_URI` (env `DATABASE_URL` or `sqlite:///greenlights.db`), `SQLALCHEMY_TRACK_MODIFICATIONS=False`, and `SEND_FILE_MAX_AGE_DEFAULT=30 days`.
- The application registers the routes blueprint from `green_traffic_lights/routes.py`, initializes the database via the shared `db` extension, and enables compression.
- **Running:** `flask --app app run --host 0.0.0.0 --port 8000` or `gunicorn --bind 0.0.0.0:8000 app:app` (both create the app via `create_app()`).
- **CLI command:** `flask aggregate-passes --day YYYY-MM-DD` aggregates stored traffic light passes into red/green ranges for the given UTC day (defaults to the previous day when omitted).

### Русский
- **`create_app()`** – фабрика, настраивающая приложение Flask:
  - `static_folder` указывает на проектную папку `static/`, `static_url_path=""`, чтобы отдавать PWA из корня.
  - Конфигурация из `green_traffic_lights.config.Config`, включая `SQLALCHEMY_DATABASE_URI` (переменная `DATABASE_URL` или `sqlite:///greenlights.db`), `SQLALCHEMY_TRACK_MODIFICATIONS=False` и `SEND_FILE_MAX_AGE_DEFAULT=30 дней`.
- Приложение регистрирует blueprint маршрутов из `green_traffic_lights/routes.py`, инициализирует базу через общее расширение `db` и включает сжатие.
- **Запуск:** `flask --app app run --host 0.0.0.0 --port 8000` или `gunicorn --bind 0.0.0.0:8000 app:app` (обе команды создают приложение через `create_app()`).
- **CLI-команда:** `flask aggregate-passes --day YYYY-MM-DD` агрегирует сохранённые проходы по светофорам в интервалы красного/зелёного за указанный день по UTC (по умолчанию — предыдущий день).

## Database helper (`green_traffic_lights/extensions.py`)

### English
- **`db`** – a shared `SQLAlchemy` instance used by models and blueprints. Tables are created inside the application factory.

### Русский
- **`db`** – общий экземпляр `SQLAlchemy`, используемый моделями и blueprint'ами. Таблицы создаются внутри фабрики приложения.

## Data model (`green_traffic_lights/models/click_event.py`)

### English
- **`ClickEvent`** – SQLAlchemy model representing a click report:
  - `id` (int, PK, autoincrement)
  - `lat`, `lon` (float, required) – geographic coordinates.
  - `speed` (float, optional) – speed in km/h if available.
  - `timestamp` (datetime, timezone-aware, required) – when the click happened.
  - `created_at` (datetime, timezone-aware, default `func.now()`) – server insert time.
- Records are created by `save_click_to_db` inside `green_traffic_lights/routes.py`.

### Русский
- **`ClickEvent`** – модель SQLAlchemy, описывающая отправку клика:
  - `id` (int, PK, autoincrement)
  - `lat`, `lon` (float, обязательные) – координаты.
  - `speed` (float, опционально) – скорость в км/ч, если доступна.
  - `timestamp` (datetime с таймзоной, обязательное) – момент клика.
  - `created_at` (datetime с таймзоной, по умолчанию `func.now()`) – время вставки на сервере.
- Записи создаются функцией `save_click_to_db` из `routes.py`.

## Traffic light service (`green_traffic_lights/services/traffic_lights.py`)

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
  from green_traffic_lights.services.traffic_lights import validate_click_distance

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
  from green_traffic_lights.services.traffic_lights import validate_click_distance

  lat, lon = 55.75, 37.61
  validation = validate_click_distance(lat, lon)
  if validation:
      payload, status = validation
      # Обработать ответ 400
  else:
      # Продолжить сохранение клика
  ```

## Routes (`green_traffic_lights/routes.py`)

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
      "timestamp": "2024-01-01T12:00:00Z",
      "inferred_state": {   // optional inferred pass details from the client
        "light_id": "48",
        "color": "green",  // or "red"
        "speed_profile": [32.1, 28.4, 30.0],
        "pass_timestamp": "2024-01-01T12:00:05Z"
      }
    }
    ```
  - **Validation:**
    - Ensures numeric `lat`/`lon`, optional numeric `speed`, ISO 8601 `timestamp` with timezone.
    - Optional `inferred_state` must include a light identifier, `color` of `green`/`red`, a JSON-serializable `speed_profile`, and a timezone-aware `pass_timestamp`.
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
  - **Helper:** `save_click_to_db(lat, lon, speed, timestamp, inferred_pass=None)` – creates and commits a `ClickEvent` record and optionally a linked `TrafficLightPass`.
  - **`api_light_ranges(light_identifier)`** – `GET /api/lights/<light_identifier>/ranges` returns aggregated ranges for a specific light.
    - **Query params:** `day` optional (`YYYY-MM-DD`, UTC). Defaults to the previous UTC date to match aggregation.
  - **Response:** `{ "light_identifier": "48", "ranges": [{ "color": "green", "start_time": "2024-01-01T12:00:05+00:00", "end_time": "2024-01-01T12:00:30+00:00", "day": "2024-01-01" }] }`.

### Aggregation (`green_traffic_lights/services/aggregation.py`)

- **`aggregate_passes_for_day(target_day=None)`** – aggregates saved `TrafficLightPass` rows into consolidated `TrafficLightRange` windows for the previous UTC day by default; reruns replace existing data for idempotency.
- **`get_ranges_for_light(light_identifier, day=None)`** – returns stored aggregated ranges for a specific light and day (defaults to the previous UTC day to mirror aggregation) ordered by start time.

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
      "timestamp": "2024-01-01T12:00:00Z",
      "inferred_state": {   // опциональная инференция состояния светофора
        "light_id": "48",
        "color": "green",  // или "red"
        "speed_profile": [32.1, 28.4, 30.0],
        "pass_timestamp": "2024-01-01T12:00:05Z"
      }
    }
    ```
  - **Валидация:**
    - Проверка числовых `lat`/`lon`, опциональной числовой `speed`, ISO 8601 `timestamp` с таймзоной.
    - Опциональный блок `inferred_state` должен содержать идентификатор светофора, `color` со значением `green`/`red`, JSON-сериализуемый `speed_profile` и `pass_timestamp` с таймзоной.
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
- **Вспомогательная функция:** `save_click_to_db(lat, lon, speed, timestamp, inferred_pass=None)` – создаёт и фиксирует запись `ClickEvent`, а при наличии инференции — связанную `TrafficLightPass`.
  - **`api_light_ranges(light_identifier)`** – `GET /api/lights/<light_identifier>/ranges` возвращает агрегированные интервалы для конкретного светофора.
    - **Параметры запроса:** `day` опциональный (`YYYY-MM-DD`, UTC). По умолчанию — предыдущий день по UTC, чтобы совпадать с агрегацией.
  - **Ответ:** `{ "light_identifier": "48", "ranges": [{ "color": "green", "start_time": "2024-01-01T12:00:05+00:00", "end_time": "2024-01-01T12:00:30+00:00", "day": "2024-01-01" }] }`.

### Агрегация (`green_traffic_lights/services/aggregation.py`)

- **`aggregate_passes_for_day(target_day=None)`** – агрегирует сохранённые `TrafficLightPass` за предыдущий день (по умолчанию) в интервалы `TrafficLightRange`; повторные запуски перезаписывают данные за выбранную дату.
- **`get_ranges_for_light(light_identifier, day=None)`** – возвращает сохранённые интервалы для указанного светофора и дня (по умолчанию — предыдущий день по UTC, чтобы совпадать с агрегацией), отсортированные по началу.

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

