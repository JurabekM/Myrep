# Smart Moliya - AI Service (FastAPI + PyTorch, CPU-only)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY ai_service/requirements.txt .
# CPU-only PyTorch - image hajmini ~5GB dan ~1.5GB gacha kamaytiradi
RUN pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

COPY ai_service/app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
