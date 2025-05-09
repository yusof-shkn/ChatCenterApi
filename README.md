Вот как можно дополнить раздел **"Установка и запуск"** в вашей документации, добавив подробную инструкцию по **Docker-сборке** и запуску проекта:

---

## Установка и запуск

### Требования:

* Python 3.10+ *(только для локальной разработки)*
* Docker
* PostgreSQL 14+ *(в Docker-сборке поднимается автоматически)*
* Docker Compose

---

### 1. Клонировать репозиторий

```bash
git clone https://github.com/yusof-shkn/chat-center-api.git
cd chat-center-api
```

---

### 2. Создать и настроить `.env` файл

Создайте `.env` в корне проекта:

```ini
POSTGRES_URL=postgresql://postgres:postgres@db:5432/main
MONGO_URI=mongodb://mongo:27017
REDIS_URL=redis://redis:6379
NLP_MODEL_NAME=ru_core_news_md
```

> ⚠️ Убедитесь, что переменные совпадают с настройками в `docker-compose.yml`

---

### 3. Построить и запустить контейнеры с помощью Docker


#### 3.1 Запуск проекта

```bash
docker compose up -d
```

Это запустит:

* FastAPI API-сервер (`app`)
* PostgreSQL (`db`)
* Redis (`redis`)
* MongoDB (`mongo`)

#### 3.2 Проверка

После запуска перейдите в браузере на:
[http://localhost:8000/docs](http://localhost:8000/docs) — авто-документация Swagger

---

### 4. Перезапуск с новыми переменными `.env`

Если вы отредактировали `.env`, выполните:

```bash
docker compose up -d --build
```

Это пересоберёт образ, пересоздаст контейнеры и применит новые переменные.

---

### 5. Локальный запуск без Docker *(опционально)*

#### Установка зависимостей:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Запуск сервера:

```bash
uvicorn app.main:app --reload
```

---

Хотите, чтобы я добавил пример `docker-compose.yml` тоже?
