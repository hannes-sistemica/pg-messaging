-- PostgreSQL Messaging System Schema

-- Make sure we're in the correct database
\c messaging;

-- Check if the HTTP extension is available
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_available_extensions 
        WHERE name = 'http' AND installed_version IS NULL
    ) THEN
        RAISE NOTICE 'Enabling HTTP extension...';
        CREATE EXTENSION IF NOT EXISTS http;
    ELSE
        RAISE WARNING 'HTTP extension not available! Some functionality will be limited.';
    END IF;
END
$$;

-- Messages table - Central repository of all messages
CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  message_type VARCHAR(100) NOT NULL,
  namespace VARCHAR(100) NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create indices for faster lookup
CREATE INDEX idx_messages_type_namespace ON messages(message_type, namespace);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Subscriptions table - Defines routing rules
CREATE TABLE subscriptions (
  id SERIAL PRIMARY KEY,
  client_id VARCHAR(100) NOT NULL,
  message_type VARCHAR(100) NOT NULL,
  namespace VARCHAR(100) NOT NULL,
  delivery_mode VARCHAR(20) NOT NULL CHECK (delivery_mode IN ('async', 'http', 'notify')),
  webhook_url VARCHAR(255), -- Only for http clients
  notification_channel VARCHAR(100), -- Only for notify clients
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(client_id, message_type, namespace)
);

-- Create indices for faster subscription lookup
CREATE INDEX idx_subscriptions_client ON subscriptions(client_id);
CREATE INDEX idx_subscriptions_type_namespace ON subscriptions(message_type, namespace);
CREATE INDEX idx_subscriptions_delivery_mode ON subscriptions(delivery_mode);

-- Message delivery tracking table
CREATE TABLE message_delivery (
  message_id INTEGER REFERENCES messages(id),
  client_id VARCHAR(100) NOT NULL,
  status VARCHAR(50) DEFAULT 'new',
  created_at TIMESTAMP DEFAULT NOW(),
  delivered_at TIMESTAMP NULL,
  push_attempted_at TIMESTAMP NULL,
  push_status VARCHAR(50) NULL,
  retry_count INTEGER DEFAULT 0,
  error_details TEXT NULL,
  UNIQUE(message_id, client_id)
);

-- Create indices for faster delivery lookup
CREATE INDEX idx_message_delivery_client_status ON message_delivery(client_id, status);
CREATE INDEX idx_message_delivery_message ON message_delivery(message_id);
CREATE INDEX idx_message_delivery_status ON message_delivery(status);