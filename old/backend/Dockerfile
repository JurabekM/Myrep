FROM python:3.12-slim AS base

# Tesseract for OCR (uz-lotin uses Latin script; uzb/rus/eng language packs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-uzb tesseract-ocr-rus tesseract-ocr-eng \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && pip uninstall -y ai-business-advisor || true

FROM base AS runtime
RUN useradd --create-home --shell /usr/sbin/nologin appuser
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
