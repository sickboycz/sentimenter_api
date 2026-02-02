FROM python:3.11-slim

WORKDIR /app

# System deps (curl/wget for healthchecks, build deps for psycopg2 if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY registry /app/registry
COPY openapi /app/openapi

EXPOSE 8000

ENV PYTHONPATH=/app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
