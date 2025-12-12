# Green Traffic Lights PWA Scaffold

This repository contains a minimal Flask scaffold for a Progressive Web App (PWA). It serves static assets from the `static/` directory and exposes a placeholder API route at `/api/click` for future enhancements. Gunicorn is included for production-style serving.

## Requirements
- Python 3.14 (or the nearest available 3.x version on your platform)
- pip
- (Recommended) `python -m venv` for isolating dependencies

## Installation
1. Clone the repository and change into the project directory:
   ```bash
   git clone <repo-url>
   cd green-traffic-lights
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   - On Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the server
### Ubuntu (desktop or server)
- Development server (auto-reload, not for production):
  ```bash
  flask --app app run --host 0.0.0.0 --port 8000
  ```
- Gunicorn (recommended for production-like usage):
  ```bash
  gunicorn --bind 0.0.0.0:8000 app:app
  ```
- Open a browser to `http://localhost:8000`.

### Android (Termux)
1. Install Python in Termux: `pkg install python`.
2. (Optional) Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run Flask dev server: `flask --app app run --host 0.0.0.0 --port 8000`.
   - Or Gunicorn (if installed): `gunicorn --bind 0.0.0.0:8000 app:app`.
5. Visit `http://127.0.0.1:8000` from the same device, or use the LAN IP to access from another device.

### Windows
- Run from Command Prompt or PowerShell after activating the virtual environment:
  ```powershell
  flask --app app run --host 0.0.0.0 --port 8000
  ```
- Or with Gunicorn via WSL/Ubuntu or native if available:
  ```bash
  gunicorn --bind 0.0.0.0:8000 app:app
  ```
- Open `http://localhost:8000` in your browser.

## Project structure
Core logic lives in the `green_traffic_lights/` package for easier navigation and reuse.
```
project/
├─ app.py
├─ green_traffic_lights/
│  ├─ __init__.py          # create_app factory
│  ├─ config.py            # default configuration values
│  ├─ extensions.py        # shared SQLAlchemy instance
│  ├─ routes.py            # Flask blueprint and handlers
│  ├─ models/
│  │  └─ click_event.py    # ClickEvent model
│  └─ services/
│     └─ traffic_lights.py # distance validation helpers
├─ light_traffics.json
├─ requirements.txt
└─ static/
   ├─ index.html
   ├─ styles.css
   ├─ main.js
   ├─ manifest.json
   ├─ service-worker.js
   └─ icons/
      ├─ icon-192.png
      └─ icon-512.png
```

## Notes
- Static files for the PWA live under `static/` and are served from the app root.
- The `/api/click` endpoint validates coordinates against nearby traffic lights and stores accepted clicks in the database.
- Configure the database URI or traffic lights file via environment variables (`DATABASE_URL`, `TRAFFIC_LIGHTS_FILE`).

# Каркас PWA "Green Traffic Lights"

Этот репозиторий содержит минимальный каркас Flask для прогрессивного веб-приложения (PWA). Он обслуживает статические ресурсы из каталога `static/` и принимает клики через API `/api/click`, проверяя расстояние до ближайшего светофора и сохраняя данные. Gunicorn включён для продакшн-подобного запуска.

## Требования
- Python 3.14 (или самая близкая доступная 3.x-версия для вашей платформы)
- pip
- (Рекомендуется) `python -m venv` для изоляции зависимостей

## Установка
1. Клонируйте репозиторий и перейдите в каталог проекта:
   ```bash
   git clone <repo-url>
   cd green-traffic-lights
   ```
2. Создайте и активируйте виртуальное окружение:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   - В Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

## Запуск сервера
### Ubuntu (desktop или server)
- Сервер разработки (автоперезапуск, не для продакшна):
  ```bash
  flask --app app run --host 0.0.0.0 --port 8000
  ```
- Gunicorn (рекомендуется для продакшн-подобного использования):
  ```bash
  gunicorn --bind 0.0.0.0:8000 app:app
  ```
- Откройте в браузере `http://localhost:8000`.

## Documentation / Документация

- Detailed API, function, and component reference (English & Russian): [docs/REFERENCE.md](docs/REFERENCE.md)

### Android (Termux)
1. Установите Python в Termux: `pkg install python`.
2. (Опционально) Создайте виртуальное окружение: `python -m venv .venv && source .venv/bin/activate`.
3. Установите зависимости: `pip install -r requirements.txt`.
4. Запустите dev-сервер Flask: `flask --app app run --host 0.0.0.0 --port 8000`.
   - Или Gunicorn (если установлен): `gunicorn --bind 0.0.0.0:8000 app:app`.
5. Перейдите на `http://127.0.0.1:8000` с этого же устройства или используйте LAN-IP для доступа с другого устройства.

### Windows
- Запустите из Command Prompt или PowerShell после активации виртуального окружения:
  ```powershell
  flask --app app run --host 0.0.0.0 --port 8000
  ```
- Либо через Gunicorn в WSL/Ubuntu или нативно, если доступно:
  ```bash
  gunicorn --bind 0.0.0.0:8000 app:app
  ```
- Откройте в браузере `http://localhost:8000`.

## Структура проекта
Основная логика вынесена в пакет `green_traffic_lights/`, чтобы код было проще читать и поддерживать.
```
project/
├─ app.py
├─ green_traffic_lights/
│  ├─ __init__.py          # фабрика create_app
│  ├─ config.py            # значения конфигурации по умолчанию
│  ├─ extensions.py        # общий экземпляр SQLAlchemy
│  ├─ routes.py            # blueprint и обработчики Flask
│  ├─ models/
│  │  └─ click_event.py    # модель ClickEvent
│  └─ services/
│     └─ traffic_lights.py # хелперы проверки расстояния
├─ light_traffics.json
├─ requirements.txt
└─ static/
   ├─ index.html
   ├─ styles.css
   ├─ main.js
   ├─ manifest.json
   ├─ service-worker.js
   └─ icons/
      ├─ icon-192.png
      └─ icon-512.png
```

## Примечания
- Статические файлы сейчас содержат только комментарии-заглушки.
- Конечная точка `/api/click` возвращает заглушку JSON, пока не будет добавлена бизнес-логика.
- Файлы иконок представлены текстом-заглушкой (не бинарные), поэтому их можно заменить реальными PNG-ассетами при необходимости.
