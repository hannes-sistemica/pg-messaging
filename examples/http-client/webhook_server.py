#!/usr/bin/env python3
"""
Example HTTP webhook receiver for PostgreSQL Messaging System
This server receives push notifications from Postgres HTTP triggers
"""

import os
import json
import time
import random
from flask import Flask, request, jsonify

# Configuration
PORT = int(os.environ.get("PORT", 8080))
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Create Flask app
app = Flask(__name__)


@app.route('/webhook/<client_id>', methods=['POST'])
def webhook(client_id):
    """Receive webhook notifications from PostgreSQL for a specific client"""
    # Get the message from the request
    message = request.json
    
    print(f"Processing webhook for client: {client_id}")
    # Add the client_id to the message for processing context
    message['target_client'] = client_id
    
    print('=' * 50)
    print(f"Received message {message['id']}")
    print(f"Type: {message['type']}")
    print(f"Namespace: {message['namespace']}")
    print('Payload:')
    print(json.dumps(message['payload'], indent=2))
    print('=' * 50)
    
    # Process the message
    try:
        success = process_message(message)
        if success:
            # Return success response
            return jsonify({
                'status': 'success',
                'message': f"Message {message['id']} processed successfully"
            }), 200
        else:
            # Return error response
            return jsonify({
                'status': 'error',
                'message': f"Failed to process message {message['id']}"
            }), 500
    except Exception as e:
        print(f"Error processing message {message['id']}: {str(e)}")
        # Return error response
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def process_message(message):
    """Process a single message. Implement your business logic here."""
    client_id = message.get('target_client', 'unknown')
    
    # Simulate processing time
    time.sleep(0.5)
    
    # Different success rates for different clients (for demonstration)
    success_probability = {
        'notification-service': 0.95,  # 95% success
        'shipping-service': 0.90,      # 90% success
        'customer-service': 0.85       # 85% success
    }.get(client_id, 0.90)             # Default 90% success
    
    if random.random() < success_probability:
        print(f"Successfully processed message {message['id']} for client {client_id}")
        return True
    else:
        print(f"Failed to process message {message['id']} for client {client_id}")
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return "OK", 200


@app.route('/clients', methods=['GET'])
def list_clients():
    """List supported clients"""
    clients = {
        'notification-service': {
            'description': 'Handles notification delivery to end users',
            'success_rate': '95%'
        },
        'shipping-service': {
            'description': 'Manages order fulfillment and shipping',
            'success_rate': '90%'
        },
        'customer-service': {
            'description': 'Handles customer account actions',
            'success_rate': '85%'
        }
    }
    return jsonify(clients)


if __name__ == '__main__':
    print(f"HTTP webhook server starting on port {PORT}")
    print("Ready to receive messages from PostgreSQL")
    print("Available webhook endpoints:")
    print(f" - http://localhost:{PORT}/webhook/notification-service")
    print(f" - http://localhost:{PORT}/webhook/shipping-service")
    print(f" - http://localhost:{PORT}/webhook/customer-service")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)