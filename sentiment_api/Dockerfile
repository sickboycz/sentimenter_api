FROM python:3.11-slim

WORKDIR /app

# Install deps (longer timeout/retries for slow PyPI)
COPY pyproject.toml README.md ./
ENV PIP_DEFAULT_TIMEOUT=300 PIP_RETRIES=5
ARG INSTALL_DEBUGPY=0
ARG INSTALL_DOCKER_CLI=1
RUN pip install --no-cache-dir --timeout 300 -e . \
    && if [ "$INSTALL_DEBUGPY" = "1" ]; then pip install --no-cache-dir debugpy; fi \
    && if [ "$INSTALL_DOCKER_CLI" = "1" ]; then apt-get update && apt-get install -y --no-install-recommends docker.io ca-certificates && rm -rf /var/lib/apt/lists/*; fi

COPY sentiment_api ./sentiment_api
COPY scripts ./scripts

ENV PYTHONUNBUFFERED=1
EXPOSE 8080 5678

CMD ["python", "-m", "uvicorn", "sentiment_api.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
