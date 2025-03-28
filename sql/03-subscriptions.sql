-- Sample subscriptions for testing

-- Clear any existing subscriptions
TRUNCATE subscriptions CASCADE;

-- Async clients (pull-based)
INSERT INTO subscriptions (
  client_id, 
  message_type, 
  namespace, 
  delivery_mode
) VALUES 
('analytics-service', 'order_created', 'commerce', 'async'),
('reporting-service', 'order_created', 'commerce', 'async'),
('inventory-service', 'product_updated', 'catalog', 'async'),
('audit-service', '*', '*', 'async');

-- HTTP push clients with path parameters
INSERT INTO subscriptions (
  client_id, 
  message_type, 
  namespace, 
  delivery_mode, 
  webhook_url
) VALUES 
('notification-service', 'order_created', 'commerce', 'http', 'http://localhost:8080/webhook/notification-service'),
('shipping-service', 'order_paid', 'commerce', 'http', 'http://localhost:8080/webhook/shipping-service'),
('customer-service', 'customer_registered', 'accounts', 'http', 'http://localhost:8080/webhook/customer-service');

-- NOTIFY clients
INSERT INTO subscriptions (
  client_id, 
  message_type, 
  namespace, 
  delivery_mode, 
  notification_channel
) VALUES 
('dashboard-service', 'order_created', 'commerce', 'notify', 'dashboard_updates'),
('admin-portal', 'user_login', 'accounts', 'notify', 'security_events'),
('monitoring-service', 'system_alert', 'operations', 'notify', 'system_monitors');

-- Note: In the above sample, 'audit-service' subscribes to all message types
-- In a real implementation, you might want to handle wildcards in the trigger functions