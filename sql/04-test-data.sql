-- Sample test data for the messaging system

-- Clear existing data
TRUNCATE messages CASCADE;
ALTER SEQUENCE messages_id_seq RESTART WITH 1;

-- Insert test messages
INSERT INTO messages (message_type, namespace, payload) VALUES
(
  'order_created',
  'commerce',
  '{
    "order_id": "ORD-12345",
    "customer_id": "CUST-789",
    "items": [
      {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
      {"product_id": "PROD-005", "quantity": 1, "price": 49.95}
    ],
    "total": 109.93,
    "created_at": "2025-03-28T09:15:23Z"
  }'::jsonb
),
(
  'order_paid',
  'commerce',
  '{
    "order_id": "ORD-12345",
    "payment_id": "PAY-567890",
    "amount": 109.93,
    "payment_method": "credit_card",
    "paid_at": "2025-03-28T09:20:45Z"
  }'::jsonb
),
(
  'product_updated',
  'catalog',
  '{
    "product_id": "PROD-001",
    "name": "Premium Wireless Headphones",
    "price": 34.99,
    "stock_quantity": 45,
    "updated_at": "2025-03-28T08:30:00Z"
  }'::jsonb
),
(
  'customer_registered',
  'accounts',
  '{
    "customer_id": "CUST-901",
    "email": "new.customer@example.com",
    "name": "New Customer",
    "registered_at": "2025-03-28T10:05:12Z"
  }'::jsonb
),
(
  'user_login',
  'accounts',
  '{
    "user_id": "USER-456",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "login_at": "2025-03-28T11:22:33Z" 
  }'::jsonb
),
(
  'system_alert',
  'operations',
  '{
    "alert_id": "ALT-789",
    "severity": "warning",
    "component": "database-server",
    "message": "High CPU usage detected",
    "details": {
      "cpu_usage": 85.2,
      "memory_usage": 67.8,
      "disk_space": 35.4
    },
    "timestamp": "2025-03-28T12:00:01Z"
  }'::jsonb
);

-- Query to see message delivery status
SELECT 
  m.id,
  m.message_type,
  m.namespace,
  md.client_id,
  md.status,
  s.delivery_mode
FROM messages m
JOIN message_delivery md ON m.id = md.message_id
JOIN subscriptions s ON md.client_id = s.client_id 
  AND (s.message_type = m.message_type OR s.message_type = '*')
  AND (s.namespace = m.namespace OR s.namespace = '*')
ORDER BY m.id, md.client_id;