FROM python:3.11-slim

WORKDIR /app

# Install deps (longer timeout/retries for slow PyPI)
COPY pyproject.toml README.md ./
ENV PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=5
ARG INSTALL_DEBUGPY=0
RUN pip install --no-cache-dir --timeout 300 -e . \
    && if [ "$INSTALL_DEBUGPY" = "1" ]; then pip install --no-cache-dir debugpy; fi

COPY sentiment_api ./sentiment_api
COPY scripts ./scripts

ENV PYTHONUNBUFFERED=1
EXPOSE 8080 5678

CMD ["python", "-m", "uvicorn", "sentiment_api.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
