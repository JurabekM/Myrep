# Smart Moliya - Admin Panel (FastAPI + Jinja2)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY admin_panel/requirements.txt .
RUN pip install -r requirements.txt

COPY admin_panel/app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8200

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
