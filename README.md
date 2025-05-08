**Чат-центр API (FastAPI)**  
**Автор**: Yusof Shokohyan  

---

## Особенности проекта  
Многоязычный чат-бот с поддержкой русского, английского и таджикского языков. Обрабатывает контекстные диалоги, интенты и сущности на основе YAML-конфигураций.

### Основные возможности:  
- Обработка естественного языка (NLP) через SpaCy  
- Поддержка многошаговых диалогов  
- Интеграция с PostgreSQL, MongoDB и Redis  
- Локализованные ответы на русском, таджикском и английском  

---

## Технологический стек  
- **Backend**: FastAPI + Uvicorn  
- **Базы данных**: PostgreSQL (основные данные), MongoDB (история сообщений)  
- **Кэш**: Redis  
- **NLP**: SpaCy с кастомными YAML-конфигами  
- **Деплоймент**: Docker, Nginx  

---

## Установка и запуск  

### Требования:  
- Python 3.10+  
- Docker  
- PostgreSQL 14+  

### Инструкции:  
1. Клонировать репозиторий:  
   ```bash 
   git clone https://github.com/yusof-shkn/chat-center-api.git
   cd chat-center-api
   ```

2. Установить зависимости:  
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Настроить `.env` файл:  
   ```ini
   POSTGRES_URL=postgresql://user:pass@localhost:5432/main
   MONGO_URI=mongodb://localhost:27017
   NLP_MODEL_NAME=ru_core_news_md
   ```

4. Запустить сервисы:  
   ```bash
   docker-compose up -d  # Запуск PostgreSQL и Redis
   uvicorn app.main:app --reload  # Запуск FastAPI
   ```

---

## Конфигурация бота  
### Пример YAML-конфига (русский):  
```yaml
greeting:
  patterns:
    - ["привет"]
    - ["здравствуйте"]
  responses:
    - "Привет, {name}! Чем могу помочь?"
    
weather:
  patterns:
    - ["погода"]
    - ["температура"]
  responses:
    - "В каком городе нужен прогноз?"
```

---

## Взаимодействие с ботом  
### Пример запроса через API:  
**Endpoint**: `POST /api/message`  
**Тело запроса**:  
```json
{
  "text": "Привет, какая погода в Душанбе?",
  "user_id": "USER123",
  "language": "ru"
}
```

**Ответ**:  
```json
{
  "intent": "weather",
  "response": "В Душанбе сейчас солнечно, 28°C",
  "confidence": 0.92
}
```

---

## Архитектура NLP  
1. **Токенизация текста**  
2. **Поиск интентов** по шаблонам из YAML  
3. **Извлечение сущностей** (города, даты)  
4. **Генерация ответа** на основе конфигурации  

```mermaid
graph TD
    A[Пользователь] --> B{API}
    B --> C[NLP Engine]
    C --> D[Поиск интентов]
    D --> E[Извлечение сущностей]
    E --> F[Генерация ответа]
    F --> B
    B --> A
```

---

## Лицензия и контакты  
**Лицензия**: MIT License  
**Разработчик**: Yusof Shokohyan  
- GitHub: [yusof-shkn](https://github.com/yusof-shkn)  
- Telegram: [@yusof_shkn](https://t.me/Yusof_0090)  
- Email: yusof.shokohyan4@gmail.com  

---

**Примечание**: Для работы с таджикским языком добавьте соответствующие YAML-конфиги и модель SpaCy для таджикского языка.