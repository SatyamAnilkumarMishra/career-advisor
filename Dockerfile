
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . .
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/chroma_db /app/hf_cache \
    && chown -R appuser:appuser /app
USER appuser

ENV CHROMA_PERSIST_DIR=/app/chroma_db \
    HF_HOME=/app/hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/hf_cache

EXPOSE 7860

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "7860"]
