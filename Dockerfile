FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y gcc libpoppler-cpp-dev pkg-config poppler-utils && \
    apt-get clean

# Create directories for static and templates
RUN mkdir -p /app/static /app/templates

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify directory structure
RUN echo "Current directory: $(pwd)" && \
    echo "Directory structure:" && \
    ls -lR && \
    echo "Templates directory contents:" && \
    ls -l templates/ && \
    echo "Static directory contents:" && \
    ls -l static/

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000", "--timeout-keep-alive", "300"]
