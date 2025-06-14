FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y gcc libpoppler-cpp-dev pkg-config poppler-utils && \
    apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify templates exist
RUN echo "Verifying templates directory:" && \
    mkdir -p templates && \
    ls -l templates/ && \
    echo "Creating static directories:" && \
    mkdir -p static/css static/js

# Create minimal style.css if missing
RUN if [ ! -f "static/css/style.css" ]; then \
        echo "/* Fallback CSS */ body { font-family: Arial, sans-serif; }" > static/css/style.css; \
    fi

# Create minimal app.js if missing
RUN if [ ! -f "static/js/app.js" ]; then \
        echo "// Fallback JS" > static/js/app.js; \
    fi

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000", "--timeout-keep-alive", "300"]
