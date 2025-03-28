-- PostgreSQL Messaging System Triggers

-- Function for async message distribution
CREATE OR REPLACE FUNCTION distribute_async_message() RETURNS TRIGGER AS $$
DECLARE
  subscription RECORD;
BEGIN
  -- For each matching async subscription
  FOR subscription IN 
    SELECT * FROM subscriptions 
    WHERE (message_type = NEW.message_type OR message_type = '*')
    AND (namespace = NEW.namespace OR namespace = '*')
    AND delivery_mode = 'async'
  LOOP
    -- Create delivery record
    INSERT INTO message_delivery (message_id, client_id)
    VALUES (NEW.id, subscription.client_id);
  END LOOP;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Check if HTTP extension is available
DO $$
DECLARE
  http_available BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = 'http'
  ) INTO http_available;

  IF http_available THEN
    -- Create the HTTP function only if the extension is available
    EXECUTE 
    'CREATE OR REPLACE FUNCTION distribute_http_message() RETURNS TRIGGER AS $http_func$
    DECLARE
      subscription RECORD;
      http_response http_response;
      error_text TEXT;
    BEGIN
      -- For each matching HTTP subscription
      FOR subscription IN 
        SELECT * FROM subscriptions 
        WHERE (message_type = NEW.message_type OR message_type = ''*'')
        AND (namespace = NEW.namespace OR namespace = ''*'')
        AND delivery_mode = ''http''
        AND webhook_url IS NOT NULL
      LOOP
        -- Create delivery record
        INSERT INTO message_delivery (
          message_id, 
          client_id, 
          status, 
          push_attempted_at
        )
        VALUES (
          NEW.id, 
          subscription.client_id, 
          ''push_attempted'', 
          NOW()
        );
        
        -- Try HTTP push with error handling
        BEGIN
          -- Make HTTP request
          http_response := http_post(
            subscription.webhook_url,
            json_build_object(
              ''id'', NEW.id, 
              ''type'', NEW.message_type,
              ''namespace'', NEW.namespace,
              ''payload'', NEW.payload
            )::text,
            ''application/json''
          );
          
          -- Update status based on response
          IF http_response.status >= 200 AND http_response.status < 300 THEN
            UPDATE message_delivery
            SET status = ''push_succeeded'',
                push_status = http_response.status::text
            WHERE message_id = NEW.id AND client_id = subscription.client_id;
          ELSE
            UPDATE message_delivery
            SET status = ''push_failed'',
                push_status = http_response.status::text,
                error_details = http_response.content
            WHERE message_id = NEW.id AND client_id = subscription.client_id;
          END IF;
        EXCEPTION WHEN OTHERS THEN
          -- Capture error details
          GET STACKED DIAGNOSTICS error_text = MESSAGE_TEXT;
          
          -- Update with error info
          UPDATE message_delivery
          SET status = ''push_failed'',
              push_status = ''error'',
              error_details = error_text
          WHERE message_id = NEW.id AND client_id = subscription.client_id;
        END;
      END LOOP;
      
      RETURN NEW;
    END;
    $http_func$ LANGUAGE plpgsql;';
  ELSE
    -- Create a dummy HTTP function if the extension is not available
    EXECUTE 
    'CREATE OR REPLACE FUNCTION distribute_http_message() RETURNS TRIGGER AS $http_func$
    BEGIN
      RAISE WARNING ''HTTP extension not available - HTTP push delivery is disabled'';
      RETURN NEW;
    END;
    $http_func$ LANGUAGE plpgsql;';
  END IF;
END$$;

-- Function for NOTIFY message distribution
CREATE OR REPLACE FUNCTION distribute_notify_message() RETURNS TRIGGER AS $$
DECLARE
  subscription RECORD;
  notification_payload TEXT;
BEGIN
  -- Convert message to JSON text
  notification_payload := json_build_object(
    'id', NEW.id,
    'type', NEW.message_type,
    'namespace', NEW.namespace,
    'payload', NEW.payload
  )::text;

  -- For each matching notify subscription
  FOR subscription IN 
    SELECT * FROM subscriptions 
    WHERE (message_type = NEW.message_type OR message_type = '*')
    AND (namespace = NEW.namespace OR namespace = '*')
    AND delivery_mode = 'notify'
    AND notification_channel IS NOT NULL
  LOOP
    -- Create delivery record
    INSERT INTO message_delivery (message_id, client_id, status)
    VALUES (NEW.id, subscription.client_id, 'notified');
    
    -- Send notification
    PERFORM pg_notify(subscription.notification_channel, notification_payload);
  END LOOP;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to messages table
CREATE TRIGGER async_distribution
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION distribute_async_message();

CREATE TRIGGER http_distribution
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION distribute_http_message();

CREATE TRIGGER notify_distribution
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION distribute_notify_message();

-- Check if HTTP extension is available for the retry function
DO $$
DECLARE
  http_available BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = 'http'
  ) INTO http_available;

  IF http_available THEN
    -- Create the HTTP retry function only if the extension is available
    EXECUTE 
    'CREATE OR REPLACE FUNCTION retry_failed_http_push(p_message_id INTEGER, p_client_id VARCHAR) RETURNS BOOLEAN AS $retry_func$
    DECLARE
      v_subscription RECORD;
      v_message RECORD;
      http_response http_response;
      error_text TEXT;
    BEGIN
      -- Get message data
      SELECT * INTO v_message FROM messages WHERE id = p_message_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION ''Message % not found'', p_message_id;
      END IF;
      
      -- Get subscription data
      SELECT * INTO v_subscription FROM subscriptions 
      WHERE client_id = p_client_id 
      AND (message_type = v_message.message_type OR message_type = ''*'')
      AND (namespace = v_message.namespace OR namespace = ''*'')
      AND delivery_mode = ''http'';
      
      IF NOT FOUND THEN
        RAISE EXCEPTION ''HTTP subscription not found for client %'', p_client_id;
      END IF;
      
      -- Update retry attempt
      UPDATE message_delivery
      SET retry_count = retry_count + 1,
          push_attempted_at = NOW(),
          status = ''push_attempted''
      WHERE message_id = p_message_id AND client_id = p_client_id;
      
      -- Try HTTP push again
      BEGIN
        http_response := http_post(
          v_subscription.webhook_url,
          json_build_object(
            ''id'', v_message.id, 
            ''type'', v_message.message_type,
            ''namespace'', v_message.namespace,
            ''payload'', v_message.payload
          )::text,
          ''application/json''
        );
        
        -- Update status based on response
        IF http_response.status >= 200 AND http_response.status < 300 THEN
          UPDATE message_delivery
          SET status = ''push_succeeded'',
              push_status = http_response.status::text
          WHERE message_id = p_message_id AND client_id = p_client_id;
          
          RETURN TRUE;
        ELSE
          UPDATE message_delivery
          SET status = ''push_failed'',
              push_status = http_response.status::text,
              error_details = http_response.content
          WHERE message_id = p_message_id AND client_id = p_client_id;
          
          RETURN FALSE;
        END IF;
      EXCEPTION WHEN OTHERS THEN
        -- Capture error details
        GET STACKED DIAGNOSTICS error_text = MESSAGE_TEXT;
        
        -- Update with error info
        UPDATE message_delivery
        SET status = ''push_failed'',
            push_status = ''error'',
            error_details = error_text
        WHERE message_id = p_message_id AND client_id = p_client_id;
        
        RETURN FALSE;
      END;
    END;
    $retry_func$ LANGUAGE plpgsql;';
  ELSE
    -- Create a dummy retry function if the extension is not available
    EXECUTE 
    'CREATE OR REPLACE FUNCTION retry_failed_http_push(p_message_id INTEGER, p_client_id VARCHAR) RETURNS BOOLEAN AS $retry_func$
    BEGIN
      RAISE WARNING ''HTTP extension not available - HTTP push retry is disabled'';
      RETURN FALSE;
    END;
    $retry_func$ LANGUAGE plpgsql;';
  END IF;
END$$;