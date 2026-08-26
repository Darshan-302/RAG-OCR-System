FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config ./config
COPY src ./src
COPY cli ./cli

# Create data directories
RUN mkdir -p data/{input,output,documents,chroma_db} logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose ports (if needed)
# EXPOSE 8000

# Default command
CMD ["python", "cli/main.py", "--help"]
