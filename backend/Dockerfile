# Multi-arch base image: runs natively on amd64 (Linux/Windows) and arm64 (Apple Silicon).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && uvicorn faultkeeper.asgi:application --host 0.0.0.0 --port 8000"]
