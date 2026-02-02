FROM python:3.11-slim

WORKDIR /app

# Install deps (longer timeout/retries for slow PyPI)
COPY pyproject.toml README.md ./
ENV PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=5
RUN pip install --no-cache-dir --timeout 300 -e .

COPY sentiment_api ./sentiment_api

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "sentiment_api.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
