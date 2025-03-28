# PostgreSQL Event Messaging System

This repository contains a messaging system built entirely on PostgreSQL. It offers reliable and trackable message distribution patterns: asynchronous consumption, HTTP-based webhooks, and real-time notifications using PostgreSQL’s `LISTEN/NOTIFY`. Unlike Kafka or RabbitMQ, this system requires no additional infrastructure and is ideal for integrating event-driven behavior into PostgreSQL-centric environments.

---

## Overview

When a message is inserted into the `messages` table, PostgreSQL triggers automatically distribute it to all subscribed clients. Each client can choose between three delivery modes:

- **Async**: Clients poll messages when ready. This ensures durable delivery and decouples sender and receiver.
- **HTTP Push**: PostgreSQL pushes the message directly to the client’s webhook URL. This enables real-time processing but requires the endpoint to be available.
- **NOTIFY**: PostgreSQL sends a real-time event over a specified channel using `pg_notify()`. This is lightweight but does not persist delivery status.

All delivery attempts are tracked in a separate table, allowing inspection, retries, and audits.

---

## Running the System

### Option 1: Run PostgreSQL and pgAdmin (Core Services)

```bash
docker-compose up -d
```

This launches:
- PostgreSQL with the messaging schema and `pgsql-http`
- pgAdmin at [http://localhost:5050](http://localhost:5050) (default login: `admin@pgmessaging.com` / `admin`)

Clients are not started automatically. Use the next step.

### Option 2: Add Sample Clients (Services)

```bash
docker-compose -f docker-compose.yml -f docker-compose-services.yml up -d
```

This starts:
- HTTP webhook consumers (e.g., `webhook-server`)
- Async consumers (e.g., `analytics-service`, `reporting-service`)
- NOTIFY listeners (e.g., `dashboard-service`, `admin-portal`)

All services are connected via `pg-messaging-network`. You can also run them individually.

### Option 3: Local Clients, Dockerized Postgres

Start only PostgreSQL in Docker:

```bash
docker-compose up -d postgres
```

Then run a local client from source, e.g.:

```bash
cd examples/async-client
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python async_consumer.py
```

### Option 4: Everything Locally (Advanced)

Install PostgreSQL and manually run the SQL files in `sql/`. Ensure the `http` extension is available (see Dependency section). Then run publisher and clients from `examples/`.

---

## Publishing Messages

To send test messages:

```bash
cd examples/publisher
python publisher.py -f order_created.json
```

Omit `-f` to publish all messages in the folder. After publishing, you’ll see delivery stats grouped by delivery mode.

---

## Receiving Messages

### Async (Polling)

```bash
cd examples/async-client
python async_consumer.py
```

Fetches new messages from `message_delivery`, processes them, and marks them as `delivered`.

### HTTP (Webhook Receiver)

```bash
cd examples/http-client
python webhook_server.py
```

If PostgreSQL runs in Docker and the webhook is on your host:

```sql
UPDATE subscriptions
SET webhook_url = REPLACE(webhook_url, 'localhost', 'host.docker.internal')
WHERE delivery_mode = 'http';
```

### Notify (pg_notify)

```bash
cd examples/notify-client
python notify_listener.py
```

Listens on a PostgreSQL notification channel and processes messages in real time.

---

## Inspecting the System

```sql
SELECT * FROM messages ORDER BY created_at DESC;
SELECT * FROM message_delivery ORDER BY created_at DESC;
SELECT * FROM subscriptions;
```

Or connect to the container:

```bash
docker exec -it postgres-messaging psql -U postgres -d messaging
```

---

## Screenshots

**Subscriptions table:**

![Subscriptions](docs/screenshot_subscriptions_table.png)

**Message delivery tracking:**

![Delivery](docs/screenshot_message-delivery_table.png)

---

## Monitoring and Observability

All delivery attempts are tracked in `message_delivery`, with fields like status, timestamps, push status codes, and retry counts. This data allows you to build detailed observability.

### Using Views and Queries

You can create SQL views or materialized views to calculate:

- Delivery success/failure rates per client
- Average delivery delay (created_at vs. delivered_at)
- Retry counts by status
- Messages stuck in failed or pending states

These can be explored in pgAdmin or exposed via tools.

### Prometheus Integration for End-to-End Metrics

#### Publisher Instrumentation

Add to `publisher.py`:

```python
from prometheus_client import Counter, start_http_server
start_http_server(8001)

published_messages = Counter(
  'pgmsg_published_messages_total',
  'Messages published to PostgreSQL',
  ['message_type', 'namespace']
)
```

Call `.inc()` on successful publish.

#### PostgreSQL Metrics

Add to `docker-compose.yml`:

```yaml
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: postgres://postgres:postgres@postgres:5432/messaging?sslmode=disable
    ports:
      - "9187:9187"
    networks:
      - pg-messaging-network
```

Mount a `queries.yaml` with custom metrics:

```yaml
pg_message_delivery_status:
  query: |
    SELECT client_id, status, count(*) FROM message_delivery GROUP BY client_id, status;
  metrics:
    - client_id: {usage: "label"}
    - status: {usage: "label"}
    - count: {usage: "counter"}
```

#### Consumer Instrumentation

Add to your Python consumers:

```python
from prometheus_client import Counter, Histogram, start_http_server
start_http_server(8002)

processed_messages = Counter('pgmsg_processed_messages_total', 'Messages processed', ['client_id'])
processing_latency = Histogram('pgmsg_processing_seconds', 'Message processing duration', ['client_id'])
```

Wrap processing logic and use labels per client.

---

## Dependency: pgsql-http Extension

This project uses the [`pgsql-http`](https://github.com/pramsey/pgsql-http) extension for HTTP push delivery from within PostgreSQL triggers.

### What It Does

- Enables PostgreSQL to make outbound HTTP requests using `http_post()`.
- Used to push message payloads to webhook URLs from trigger functions.

### How It’s Installed

Included in the Docker build:

```dockerfile
RUN git clone https://github.com/pramsey/pgsql-http.git \
    && cd pgsql-http \
    && make \
    && make install
```

Enabled via SQL:

```sql
CREATE EXTENSION IF NOT EXISTS http;
```

### Considerations

- Use only in secure/internal environments
- Calls block the transaction; prefer async queues for large-scale traffic
- Add retries via `retry_failed_http_push()` SQL function

---

## Final Notes

This project is intended as a demonstrator. It emphasizes simplicity, auditability, and SQL-native extensibility. For production use:

### Logging and Error Handling

Use structured logs in publisher and consumers. Send logs to centralized systems like Loki or ELK to enable correlation and alerting.

### Secure Webhook Endpoints

Never expose unauthenticated webhook targets. Sign requests with HMAC:

```http
POST /webhook/client-id
X-Signature: sha256=...
```

Validate signatures in Python with a shared secret. Alternatively, enforce API tokens or IP allowlists.

### TTL and Housekeeping

Old messages can be archived or deleted via:
- `pg_cron`
- External maintenance scripts

E.g., delete messages older than 30 days or move them to a history table.

### Performance

Triggers run in-band. For high-throughput systems:
- Prefer async consumers (non-blocking)
- Avoid direct HTTP in triggers unless response is guaranteed fast
- Offload to background queues (e.g., pgmq, pg-boss, Sidekiq)

### Rate Limiting & Validation

Control access to message publishing:
- Require API keys or OAuth
- Use constraints to prevent malformed payloads
- Throttle at API gateway level if exposed externally

### Observability

Instrument end-to-end pipeline:
- Prometheus exporters on publishers and consumers
- Custom queries on PostgreSQL metrics
- Dashboards in Grafana showing delivery success, latency, and retries

---

## License

MIT — see the LICENSE file.

