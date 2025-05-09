FROM python:3.10-slim

# Create and set working directory
WORKDIR /app

# Install system dependencies for PostgreSQL and Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_md && \
    python -m spacy download xx_ent_wiki_sm && \
    python -m spacy download ru_core_news_md

# Copy application code
COPY . .

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]