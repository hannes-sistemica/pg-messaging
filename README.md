Here's a more detailed overview section:

# PostgreSQL Event Messaging System

This repository contains a messaging system built entirely on PostgreSQL. It offers reliable and trackable message distribution patterns: asynchronous consumption, HTTP-based webhooks, and real-time notifications using PostgreSQL's `LISTEN/NOTIFY`. Unlike Kafka or RabbitMQ, this system requires no additional infrastructure and is ideal for integrating event-driven behavior into PostgreSQL-centric environments.

## Repository Structure

```
.
├── README.md                    # This documentation
├── docker/                      # Docker configuration files
│   ├── pgadmin/                 # pgAdmin configuration
│   └── postgres/                # PostgreSQL configuration & extensions
├── docker-compose.yml           # Core services deployment
├── docker-compose-services.yml  # Sample clients deployment
├── examples/                    # Client implementations
│   ├── async-client/            # Pull-based consumer
│   ├── http-client/             # Webhook receiver
│   ├── notify-client/           # NOTIFY listener
│   └── publisher/               # Message publisher with samples
└── sql/                         # Database schema and triggers
```



## Overview

This system provides a complete event messaging solution with four main components:

1. **PostgreSQL Database**: The central hub that stores messages and handles delivery routing via triggers. The database schema includes:
   - `messages` table: Stores all published messages with type, namespace, and payload
   - `subscriptions` table: Defines which clients receive which messages and how
   - `message_delivery` table: Tracks delivery status for auditing and reliability

2. **pgAdmin**: A web-based administration tool that allows you to inspect messages, subscriptions, and delivery statuses through a user-friendly interface.

3. **Message Publisher**: A Python client that publishes events to the system. It adds tracking IDs and timestamps to each message for traceability.

4. **Three Types of Consumers**: The system demonstrates three distinct message consumption patterns, each with different trade-offs:

   - **Async Consumer**: Pulls messages when ready to process them. Ideal for batch operations, heavy processing, or when 100% delivery guarantee is required. Example services: analytics-service, reporting-service.
   
   - **HTTP Webhook Consumer**: Receives messages via HTTP POST from PostgreSQL. Best for real-time processing needs when the service endpoint is reliable. Example services: notification-service, shipping-service.
   
   - **NOTIFY Listener**: Gets instant lightweight notifications via PostgreSQL's pub/sub channels. Perfect for dashboards, monitoring, or other real-time UI updates. Example services: dashboard-service, admin-portal.

When a message is inserted into the `messages` table, PostgreSQL triggers automatically a distribution to all subscribed clients according to their preferred delivery mode. The system tracks all delivery attempts, allowing for comprehensive monitoring, retries of failed deliveries, and auditing of message flows.

This multi-consumer approach allows each service to consume messages in the way that best fits its requirements for reliability, latency, and processing model, while maintaining a single, consistent message source.


## Environment Variables and Settings

### Core Services

**PostgreSQL:**
- `POSTGRES_USER`: Database username (default: `postgres`)
- `POSTGRES_PASSWORD`: Database password (default: `postgres`) 
- `POSTGRES_DB`: Database name (default: `messaging`)

**pgAdmin:**
- `PGADMIN_DEFAULT_EMAIL`: Admin login email (default: `admin@pgmessaging.com`)
- `PGADMIN_DEFAULT_PASSWORD`: Admin password (default: `admin`)

### Client Services

**Async Consumer:**
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `DB_NAME`: Database name (default: `messaging`)
- `DB_USER`: Database user (default: `postgres`)
- `DB_PASS`: Database password (default: `postgres`)
- `CLIENT_ID`: Unique client identifier (default: `analytics-service`)
- `BATCH_SIZE`: Number of messages to process in one batch (default: `10`)
- `SLEEP_INTERVAL`: Seconds to wait between batches (default: `15`)

**Webhook Server:**
- `PORT`: HTTP server port (default: `8080`)
- `DEBUG`: Enable Flask debug mode (default: `false`)

**Notify Listener:**
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `DB_NAME`: Database name (default: `messaging`)
- `DB_USER`: Database user (default: `postgres`)
- `DB_PASS`: Database password (default: `postgres`)
- `CLIENT_ID`: Unique client identifier (default: `dashboard-service`)
- `CHANNEL`: PostgreSQL notification channel (default: `dashboard_updates`)

**Publisher:**
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `DB_NAME`: Database name (default: `messaging`)
- `DB_USER`: Database user (default: `postgres`)
- `DB_PASS`: Database password (default: `postgres`)

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
docker-compose -f docker-compose-services.yml up -d
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



## Publishing Messages

To send test messages:

```bash
cd examples/publisher
python publisher.py -f order_created.json
```

If you run first time:
```bash
cd examples/publisher
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python publisher.py -f order_created.json
```

Omit `-f` to publish all messages in the folder. After publishing, you’ll see delivery stats grouped by delivery mode.



## Consumer Types and Real-World Use Cases

The system supports three types of consumers, each suited for different scenarios:

### 1. Async Consumers (Pull-Based)

**Implementation:** Clients poll the database for new messages at regular intervals, process them, and mark them as delivered.

**Ideal for:**
- **Batch Processing Systems**: Analytics platforms that process data in batches
- **ETL Pipelines**: Data transfer processes that need reliable message delivery
- **Reporting Services**: Systems that generate reports from event data
- **Resource-Intensive Handlers**: Processes that require significant compute resources and need to control their own pace

**Real-World Examples in this Repository:**
- `analytics-service`: Processes order and product data to generate business insights
- `reporting-service`: Creates reports based on system events, optimized for less frequent but larger batch sizes

**Benefits:**
- Maximum reliability (messages stay in queue until confirmed as processed)
- Self-paced consumption (client controls when to fetch messages)
- Automatic backpressure handling
- No service availability requirements (client can be offline)

### 2. HTTP Webhooks (Push-Based)

**Implementation:** PostgreSQL pushes messages directly to client endpoints via HTTP POST requests.

**Ideal for:**
- **Real-Time Systems**: Services requiring immediate notification of events
- **External Integrations**: Third-party services that expose webhook endpoints
- **Microservices Communication**: Inter-service messaging within a microservices architecture
- **Notification Systems**: Alert and notification services

**Real-World Examples in this Repository:**
- `notification-service`: Sends real-time notifications to users based on system events
- `shipping-service`: Initiates shipping processes immediately when orders are paid
- `customer-service`: Updates customer profiles based on registration and account activities

**Benefits:**
- Lower latency (real-time delivery)
- No polling overhead
- Simpler client implementation (just expose an HTTP endpoint)
- Compatible with serverless architectures

### 3. NOTIFY Listeners (Real-Time)

**Implementation:** PostgreSQL sends lightweight notifications over channels that clients listen to continuously.

**Ideal for:**
- **UI Updates**: Dashboards and admin interfaces needing real-time updates
- **Cache Invalidation**: Systems that need to know when to refresh cached data
- **Real-Time Monitoring**: Alerting systems for operational events
- **Low-Latency Applications**: Trading or bidding systems where milliseconds matter

**Real-World Examples in this Repository:**
- `dashboard-service`: Updates admin dashboards in real-time with new order information
- `admin-portal`: Provides security teams with immediate notification of user login events
- `monitoring-service`: Alerts operations teams to system issues as they happen

**Benefits:**
- Lowest latency (near real-time)
- Lightweight (minimal overhead on database)
- No persistence requirements (ephemeral)
- Efficient for high-frequency events

## Receiving Messages

### Async (Polling)

Showcases clients that process in batches or operate intermittently.

- Fetches new messages from `message_delivery`.
- Processes them, and marks them as `delivered` (via SQL Update).
- Goes then to sleep for a defined while (configurable, default: 10 seconds)

Below I am using uv.
```bash
cd examples/async-client
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python async_consumer.py
```

### HTTP (Webhook Receiver)

Postgres pushes via `http_post()` function to a defined webhook (see table 'subscriptions')

- Requires reachable HTTP endpoints.
- Retries can be configured via SQL functions.

Below I am using uv.
```bash
cd examples/http-client
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python webhook_server.py
```

If PostgreSQL runs in Docker and the webhook is on your host:

```sql
UPDATE subscriptions
SET webhook_url = REPLACE(webhook_url, 'localhost', 'host.docker.internal')
WHERE delivery_mode = 'http';
```

### Notify (pg_notify)

Listens on a PostgreSQL notification channel and processes messages in real time.

- Real-time `LISTEN/NOTIFY` messages.
- No delivery tracking or retry.
- Best for monitoring and dashboard UIs.

Below I am using uv.
```bash
cd examples/notify-client
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python notify_listener.py
```


### Examples

```
➜  python publisher.py -f order_created.json
Found 1 message file(s)

Publishing order_created.json...
Successfully published message:
  Database ID: 9
  Tracking ID: zkco8M9i
  Created at: 2025-03-28 11:40:20.350708
  Type: order_created
  Namespace: commerce
  Delivery stats:
    - async: 3 recipients
    - http: 1 recipients
    - notify: 1 recipients

Summary: Published 1 of 1 messages
```

**Async Receiver:**
```
➜  python async_consumer.py
Starting async consumer for client: analytics-service
Batch size: 10, Sleep interval: 15 seconds
No new messages found. Going to sleep.
Found 2 messages to process
Processing message 8:
  Type: order_created
  Namespace: commerce
  Created at: 2025-03-28 11:40:19.331189
  Payload: {
  "items": [
    {
      "price": 29.99,
      "quantity": 2,
      "product_id": "PROD-001"
    },
    {
      "price": 49.95,
      "quantity": 1,
      "product_id": "PROD-005"
    }
  ],
  "total": 109.93,
  "sent_at": "2025-03-28T12:40:19.315700",
  "order_id": "ORD-12345",
  "customer_id": "CUST-789",
  "tracking_id": "nublNa25"
}
Successfully processed message 8
Processing message 9:
  Type: order_created
  Namespace: commerce
  Created at: 2025-03-28 11:40:20.350708
  Payload: {
  "items": [
    {
      "price": 29.99,
      "quantity": 2,
      "product_id": "PROD-001"
    },
    {
      "price": 49.95,
      "quantity": 1,
      "product_id": "PROD-005"
    }
  ],
  "total": 109.93,
  "sent_at": "2025-03-28T12:40:20.334465",
  "order_id": "ORD-12345",
  "customer_id": "CUST-789",
  "tracking_id": "zkco8M9i"
}
Successfully processed message 9
Marked 2 messages as delivered: [8, 9]
```

**Webhook Receiver:**
```
➜  python webhook_server.py
HTTP webhook server starting on port 8080
Ready to receive messages from PostgreSQL
Available webhook endpoints:
 - http://localhost:8080/webhook/notification-service
 - http://localhost:8080/webhook/shipping-service
 - http://localhost:8080/webhook/customer-service
 * Serving Flask app 'webhook_server'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://192.168.1.189:8080
Press CTRL+C to quit
Processing webhook for client: customer-service
==================================================
Received message 12
Type: customer_registered
Namespace: accounts
Payload:
{
  "name": "New Customer",
  "email": "new.customer@example.com",
  "sent_at": "2025-03-28T12:51:01.539281",
  "customer_id": "CUST-901",
  "tracking_id": "1vOXJfM9"
}
==================================================
Successfully processed message 12 for client customer-service
127.0.0.1 - - [28/Mar/2025 12:51:02] "POST /webhook/customer-service HTTP/1.1" 200 -
```

**Notify Listener:**
```
➜  python notify_listener.py
Starting NOTIFY listener for client: dashboard-service
Listening on channel: dashboard_updates
Listening for notifications on channel: dashboard_updates
.............
Received notification on channel: dashboard_updates
Processing notification for message 13:
  Type: order_created
  Namespace: commerce
  Payload: {
  "items": [
    {
      "price": 29.99,
      "quantity": 2,
      "product_id": "PROD-001"
    },
    {
      "price": 49.95,
      "quantity": 1,
      "product_id": "PROD-005"
    }
  ],
  "total": 109.93,
  "sent_at": "2025-03-28T13:03:43.563053",
  "order_id": "ORD-12345",
  "customer_id": "CUST-789",
  "tracking_id": "RNoi6JBY"
}
Successfully processed notification for message 13
```



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



## Screenshots

**Subscriptions table:**

![Subscriptions](docs/screenshot_subscriptions_table.png)

**Message delivery tracking:**

![Delivery](docs/screenshot_message-delivery_table.png)



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



## License

MIT — see the LICENSE file.

