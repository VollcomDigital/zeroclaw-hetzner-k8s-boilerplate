FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY requirements.lock /app/requirements.lock
COPY pyproject.toml /app/pyproject.toml
# Runtime image: application sources only (tests/ excluded by .dockerignore).
COPY src /app/src

RUN python -m pip install --upgrade pip && \
    python -m pip install --requirement /app/requirements.lock && \
    python -m pip install --no-deps .

USER 1000:1000

EXPOSE 8000

CMD ["python", "-m", "n8n_bridge.server"]
