FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc libpoppler-cpp-dev pkg-config && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000", "--timeout-keep-alive", "300"]
