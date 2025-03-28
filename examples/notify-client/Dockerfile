FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY notify_listener.py .

ENV DB_HOST=postgres
ENV DB_PORT=5432
ENV DB_NAME=messaging
ENV DB_USER=postgres
ENV DB_PASS=postgres
ENV CLIENT_ID=dashboard-service
ENV CHANNEL=dashboard_updates

CMD ["python", "notify_listener.py"]