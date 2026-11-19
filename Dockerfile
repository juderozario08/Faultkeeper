# Production / hosted-demo image: one container with the API, the event pipeline
# (single-process mode) and the built dashboard served on the same origin.
#   docker build -t faultkeeper .
#   docker run -p 8000:8000 -e DATABASE_URL=... -e DJANGO_SECRET_KEY=... faultkeeper

FROM node:24-slim AS dashboard
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    DEPLOY_MODE=single \
    FRONTEND_DIST=/app/dashboard \
    DJANGO_SECURE_COOKIES=true \
    PORT=8000
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY --from=dashboard /frontend/dist /app/dashboard
RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo && exec uvicorn faultkeeper.asgi:application --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
