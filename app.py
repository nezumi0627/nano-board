#!/usr/bin/env python3
import os
import eventlet
# Patch standard library for async operations
eventlet.monkey_patch()

from app import create_app

# Create Flask app and SocketIO instance
app, socketio = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Nanobot Dashboard on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
