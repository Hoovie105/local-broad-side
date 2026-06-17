# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/cannon_insta/requirements.txt ./services/cannon_insta/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r services/cannon_insta/requirements.txt

# Copy the entire application
COPY . .

# Expose port (default FastAPI port)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "services.cannon_insta.main:app", "--host", "0.0.0.0", "--port", "8000"]
