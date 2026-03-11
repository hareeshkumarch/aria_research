FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential pkg-config libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the default Chroma embeddings model (all-MiniLM-L6-v2)
# so it doesn't block the asyncio event loop during the first run at runtime.
RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2 && \
    curl -L https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz | tar -xz -C /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2

COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
