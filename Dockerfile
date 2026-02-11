FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

# System deps for psycopg, gdal (GeoDjango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

ENV PYTHONPATH=/app/pathfinder

COPY pyproject.toml .
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .

CMD ["gunicorn", "pathfinder.wsgi:application", "--bind", "0.0.0.0:8000"]
