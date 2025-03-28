#!/usr/bin/env python3
"""
PostgreSQL Messaging System Publisher
Finds and publishes message files to the messaging system with tracking IDs
"""

import os
import sys
import json
import time
import random
import string
import argparse
import psycopg2
import psycopg2.extras
from datetime import datetime
from pathlib import Path

# Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "messaging")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

# Default messages directory (relative to this script)
DEFAULT_MESSAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages")


def generate_message_id(length=8):
    """Generate a YouTube-like short ID"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def get_connection():
    """Create a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def find_message_files(directory):
    """Find all JSON message files in the specified directory"""
    if not os.path.exists(directory):
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)
    
    message_files = []
    for file in os.listdir(directory):
        if file.endswith('.json'):
            message_files.append(os.path.join(directory, file))
    
    if not message_files:
        print(f"No message files found in {directory}")
        sys.exit(1)
    
    return message_files


def load_message_file(file_path):
    """Load a message from a JSON file"""
    try:
        with open(file_path, 'r') as f:
            message_data = json.load(f)
        return message_data
    except Exception as e:
        print(f"Error loading message file {file_path}: {e}")
        return None


def publish_message(message_data, tracking_id=None):
    """Publish a message to the messaging system with tracking ID"""
    if not tracking_id:
        tracking_id = generate_message_id()
    
    timestamp = datetime.now().isoformat()
    
    # Add tracking ID and timestamp to the message payload
    if isinstance(message_data.get('payload'), dict):
        message_data['payload']['tracking_id'] = tracking_id
        message_data['payload']['sent_at'] = timestamp
    else:
        # If payload is not a dict, create a wrapper
        original_payload = message_data.get('payload')
        message_data['payload'] = {
            'data': original_payload,
            'tracking_id': tracking_id,
            'sent_at': timestamp
        }
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Extract message details
    message_type = message_data.get('type')
    namespace = message_data.get('namespace')
    payload = message_data.get('payload')
    
    if not message_type or not namespace:
        raise ValueError("Message must contain 'type' and 'namespace' fields")
    
    # Insert the message
    query = """
    INSERT INTO messages (message_type, namespace, payload)
    VALUES (%s, %s, %s)
    RETURNING id, created_at;
    """
    
    cursor.execute(query, (message_type, namespace, json.dumps(payload)))
    result = cursor.fetchone()
    message_id = result['id']
    created_at = result['created_at']
    
    # Commit the transaction
    conn.commit()
    
    # Wait a bit for message distribution to complete
    time.sleep(0.2)
    
    # Get delivery stats
    query = """
    SELECT 
        delivery_mode, 
        COUNT(*) as count
    FROM message_delivery md
    JOIN subscriptions s ON md.client_id = s.client_id
    WHERE md.message_id = %s
    GROUP BY delivery_mode;
    """
    
    cursor.execute(query, (message_id,))
    stats = cursor.fetchall()
    
    # Close the connection
    cursor.close()
    conn.close()
    
    return {
        'message_id': message_id,
        'tracking_id': tracking_id,
        'created_at': created_at,
        'delivery_stats': {row['delivery_mode']: row['count'] for row in stats}
    }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Publish messages to the messaging system')
    parser.add_argument('--dir', '-d', default=DEFAULT_MESSAGES_DIR, 
                        help=f'Directory containing message files (default: {DEFAULT_MESSAGES_DIR})')
    parser.add_argument('--file', '-f', help='Specific message file to publish (filename only, not path)')
    parser.add_argument('--tracking-id', '-t', help='Custom tracking ID (default: auto-generated)')
    parser.add_argument('--delay', type=float, default=1.0, 
                        help='Delay between messages in seconds (default: 1.0)')
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()
    
    # Ensure default messages directory exists
    os.makedirs(args.dir, exist_ok=True)
    
    if args.file:
        # Publish specific file
        file_path = os.path.join(args.dir, args.file)
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            sys.exit(1)
        
        message_files = [file_path]
    else:
        # Publish all files in directory
        message_files = find_message_files(args.dir)
        message_files.sort()  # Sort files alphabetically
    
    print(f"Found {len(message_files)} message file(s)")
    
    total_published = 0
    for file_path in message_files:
        file_name = os.path.basename(file_path)
        print(f"\nPublishing {file_name}...")
        
        message_data = load_message_file(file_path)
        if not message_data:
            print(f"Skipping {file_name} due to errors")
            continue
        
        try:
            result = publish_message(message_data, args.tracking_id)
            
            print(f"Successfully published message:")
            print(f"  Database ID: {result['message_id']}")
            print(f"  Tracking ID: {result['tracking_id']}")
            print(f"  Created at: {result['created_at']}")
            print(f"  Type: {message_data.get('type')}")
            print(f"  Namespace: {message_data.get('namespace')}")
            
            print("  Delivery stats:")
            for mode, count in result['delivery_stats'].items():
                print(f"    - {mode}: {count} recipients")
            
            total_published += 1
            
            # Don't delay after the last message
            if file_path != message_files[-1]:
                time.sleep(args.delay)
                
        except Exception as e:
            print(f"Error publishing {file_name}: {e}")
    
    print(f"\nSummary: Published {total_published} of {len(message_files)} messages")


if __name__ == "__main__":
    main()