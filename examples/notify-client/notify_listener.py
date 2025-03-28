#!/usr/bin/env python3
"""
Example NOTIFY listener client for PostgreSQL Messaging System
This client listens for real-time notifications via the LISTEN/NOTIFY mechanism.
"""

import os
import json
import sys
import time
import select
import psycopg2
import psycopg2.extensions

# Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "messaging")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
CLIENT_ID = os.environ.get("CLIENT_ID", "dashboard-service")
CHANNEL = os.environ.get("CHANNEL", "dashboard_updates")


def get_connection():
    """Create a connection to the PostgreSQL database."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    # Set isolation level to AUTOCOMMIT to enable LISTEN
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def process_notification(payload):
    """Process a notification. Implement your business logic here."""
    try:
        data = json.loads(payload)
        print(f"Processing notification for message {data['id']}:")
        print(f"  Type: {data['type']}")
        print(f"  Namespace: {data['namespace']}")
        print(f"  Payload: {json.dumps(data['payload'], indent=2)}")
        
        # Simulate processing time
        time.sleep(0.5)
        
        print(f"Successfully processed notification for message {data['id']}")
        return True
    except json.JSONDecodeError:
        print(f"Error decoding JSON payload: {payload}")
        return False
    except KeyError as e:
        print(f"Missing expected field in payload: {e}")
        return False


def main():
    """Main function to run the NOTIFY listener."""
    print(f"Starting NOTIFY listener for client: {CLIENT_ID}")
    print(f"Listening on channel: {CHANNEL}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Start listening on the specified channel
    cursor.execute(f"LISTEN {CHANNEL};")
    print(f"Listening for notifications on channel: {CHANNEL}")
    
    # Main loop
    while True:
        try:
            # Wait for notifications or timeout after 5 seconds
            if select.select([conn], [], [], 5) == ([], [], []):
                # Timeout occurred, no notification received
                sys.stdout.write(".")
                sys.stdout.flush()
            else:
                # Process all pending notifications
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    print(f"\nReceived notification on channel: {notify.channel}")
                    process_notification(notify.payload)
        
        except KeyboardInterrupt:
            print("\nShutting down listener...")
            break
        except psycopg2.OperationalError:
            print("\nDatabase connection lost. Reconnecting...")
            time.sleep(5)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"LISTEN {CHANNEL};")
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            time.sleep(5)
    
    # Clean up
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()