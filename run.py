from app import create_app
import os

app, socketio = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # eventlet is used by default with async_mode='eventlet'
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
