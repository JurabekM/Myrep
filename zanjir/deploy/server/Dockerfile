# syntax=docker/dockerfile:1.7
# ZANJIR server image (11-faza, ADR-0015). Kontekst: zanjir/server. Bazaviy image'lar digest bilan qotirilgan;
# registry'ni `REGISTRY` bilan almashtirish mumkin (masalan, ko'zgu), digest o'sha-o'sha qoladi.
ARG REGISTRY=docker.io/library
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c
ARG PYTHON_DIGEST=sha256:12316debbfb86890f6b2d825820612741ba527ad5a44e3902759141d572bfe8f

FROM ${UV_IMAGE} AS uv

FROM ${REGISTRY}/python:3.12-slim@${PYTHON_DIGEST} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# `build_ca` — ixtiyoriy: TLS'ni tekshiradigan korporativ proksi ortida build qilish uchun (prod'da berilmaydi).
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca,required=false \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --locked --no-dev --no-install-project
COPY pyproject.toml uv.lock alembic.ini ./
COPY zanjir_server ./zanjir_server
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca,required=false \
    if [ -s /run/secrets/build_ca ]; then export SSL_CERT_FILE=/run/secrets/build_ca; fi; \
    uv sync --locked --no-dev --no-editable

FROM ${REGISTRY}/python:3.12-slim@${PYTHON_DIGEST}
RUN groupadd --system --gid 10001 zanjir && useradd --system --uid 10001 --gid zanjir --no-create-home zanjir
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /src/alembic.ini /app/alembic.ini
COPY --from=build /src/zanjir_server/db/migrations /app/zanjir_server/db/migrations
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER zanjir:zanjir
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=4).status == 200 else 1)"]
# Bitta jarayon: rate limiting va kirish cheklovi jarayon xotirasida (R-02). Faqat Caddy orqali (port tashqariga ochilmaydi).
CMD ["uvicorn", "--factory", "zanjir_server.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips=*", "--no-server-header", "--no-access-log"]
