FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e .

COPY sentiment_api ./sentiment_api

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "sentiment_api.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
