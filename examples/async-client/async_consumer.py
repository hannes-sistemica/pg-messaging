#!/usr/bin/env python3
"""
Example async consumer client for PostgreSQL Messaging System
This client retrieves messages from the buffer table and processes them.
"""

import os
import json
import time
import psycopg2
import psycopg2.extras

# Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "messaging")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
CLIENT_ID = os.environ.get("CLIENT_ID", "analytics-service")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
SLEEP_INTERVAL = int(os.environ.get("SLEEP_INTERVAL", "15"))


def get_connection():
    """Create a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def fetch_pending_messages(conn, batch_size=10):
    """Fetch pending messages for this client."""
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    query = """
    SELECT 
        m.id AS message_id, 
        m.message_type, 
        m.namespace, 
        m.payload, 
        m.created_at
    FROM messages m
    INNER JOIN message_delivery md ON m.id = md.message_id
    WHERE 
        md.client_id = %s 
        AND md.status = 'new'
    ORDER BY m.created_at
    LIMIT %s
    FOR UPDATE SKIP LOCKED;
    """
    
    cursor.execute(query, (CLIENT_ID, batch_size))
    messages = cursor.fetchall()
    cursor.close()
    return messages 
    
    
def main():
    """Main function to run the consumer."""
    print(f"Starting async consumer for client: {CLIENT_ID}")
    print(f"Batch size: {BATCH_SIZE}, Sleep interval: {SLEEP_INTERVAL} seconds")
    
    while True:
        try:
            # Establish a new connection for each batch
            conn = get_connection()
            
            # Process a batch of messages
            messages = fetch_pending_messages(conn, BATCH_SIZE)
            if not messages:
                print("No new messages found. Going to sleep.")
                conn.close()
                time.sleep(SLEEP_INTERVAL)
                continue
            
            print(f"Found {len(messages)} messages to process")
            
            # Process each message
            processed_ids = []
            for message in messages:
                try:
                    success = process_message(message)
                    if success:
                        processed_ids.append(message['message_id'])
                except Exception as e:
                    print(f"Error processing message {message['message_id']}: {e}")
            
            # Mark processed messages as delivered
            if processed_ids:
                mark_as_delivered(conn, processed_ids)
            
            # Close connection
            conn.close()
            
            # Sleep between batches even if we processed messages
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("Shutting down consumer...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(SLEEP_INTERVAL)


def mark_as_delivered(conn, message_ids):
    """Mark messages as delivered."""
    if not message_ids:
        return
    
    cursor = conn.cursor()
    
    query = """
    UPDATE message_delivery
    SET status = 'delivered', delivered_at = NOW()
    WHERE message_id = ANY(%s) AND client_id = %s
    """
    
    cursor.execute(query, (message_ids, CLIENT_ID))
    conn.commit()
    cursor.close()
    
    print(f"Marked {len(message_ids)} messages as delivered: {message_ids}")


def process_message(message):
    """Process a single message. Implement your business logic here."""
    print(f"Processing message {message['message_id']}:")
    print(f"  Type: {message['message_type']}")
    print(f"  Namespace: {message['namespace']}")
    print(f"  Created at: {message['created_at']}")
    print(f"  Payload: {json.dumps(message['payload'], indent=2)}")
    
    # Simulate processing time
    time.sleep(0.5)
    
    print(f"Successfully processed message {message['message_id']}")
    return True


if __name__ == "__main__":
    main()
