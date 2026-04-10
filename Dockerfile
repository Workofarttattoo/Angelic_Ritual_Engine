FROM python:3.11-slim AS base

# System dependencies for pdf2image (poppler), tesseract, and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY pyproject.toml ./
COPY agentic_ritual_engine/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agentic_ritual_engine/ ./agentic_ritual_engine/
COPY pyproject.toml README.md ./

# Install the package itself
RUN pip install --no-cache-dir -e .

# Ensure data directories exist
RUN mkdir -p data/raw data/raw_scans data/extracted data/symbols data/thumbs

# Default environment
ENV RITUAL_DB_URL=sqlite:///data/ritual.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000 8501

# Initialise database and launch API by default
CMD ["sh", "-c", "python -m agentic_ritual_engine.main kb-init && python -m agentic_ritual_engine.main run --api-host ${API_HOST} --api-port ${API_PORT}"]
