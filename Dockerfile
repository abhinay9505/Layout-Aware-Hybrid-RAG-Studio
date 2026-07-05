# Use Python 3.11-slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV HF_HOME=/app/huggingface_cache

# Set working directory
WORKDIR /app

# Install system dependencies needed for PyMuPDF, FAISS and other libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install backend dependencies first for efficient caching
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download the Hugging Face model
RUN python -c "from langchain_huggingface import HuggingFaceEmbeddings; HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Copy the rest of the application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY run.py .

# Expose the frontend and backend ports
EXPOSE 5500
EXPOSE 8000

# Run both backend and frontend using the root run.py script
CMD ["python", "run.py"]
