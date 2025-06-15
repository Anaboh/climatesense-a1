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

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000", "--timeout-keep-alive", "300"]
