FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY async_consumer.py .

ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=messaging
ENV DB_USER=postgres
ENV DB_PASS=postgres
ENV CLIENT_ID=analytics-service
ENV BATCH_SIZE=10
ENV SLEEP_INTERVAL=5

CMD ["python", "async_consumer.py"]