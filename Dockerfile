# ============================================================
# Dockerfile — RAG Full Stack (Single Container via run.py)
# ============================================================
FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies needed by packages (FAISS, OpenCV, ffmpeg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        gcc \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv

# Ensure we use virtual environment pip to install packages
RUN /app/venv/bin/pip install --upgrade pip

# Copy backend requirements and install them inside venv
COPY backend/requirements.txt /app/backend/requirements.txt
RUN /app/venv/bin/pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend and frontend source directories
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Copy launcher script and env configuration
COPY run.py /app/run.py
COPY .env /app/.env
COPY .env /app/backend/.env

# Expose backend (8000) and frontend HTTP server (5500)
EXPOSE 8000
EXPOSE 5500

# Start both servers using the runner script in the virtual environment
CMD ["/app/venv/bin/python", "/app/run.py"]
