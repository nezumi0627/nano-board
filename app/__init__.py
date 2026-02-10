from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import eventlet
import json
import threading
import time
import requests

# Services
from .services.monitor import monitor_service
from .services.sessions import session_service
from .services.process import process_service
from .utils.version import VERSION, LAST_UPDATED

# Config
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nanobot-secret')
    CONFIG_FILE = os.path.expanduser("~/.nanobot/config.json")

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    CORS(app)
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

    # Load Config
    def load_config():
        if os.path.exists(Config.CONFIG_FILE):
            try:
                with open(Config.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    # Routes
    @app.route('/')
    def index():
        return render_template('dashboard.html', version=VERSION)

    @app.route('/api/status')
    def api_status():
        # Fallback/Initial load
        return jsonify(_get_full_status())

    @app.route('/api/control/gateway', methods=['POST'])
    def control_gateway():
        action = request.json.get('action')
        msg = "Invalid action"
        success = False
        
        if action == 'start':
            success, msg = process_service.start()
        elif action == 'stop':
            success, msg = process_service.stop()
        elif action == 'restart':
            success, msg = process_service.restart()
            
        return jsonify({"success": success, "message": msg})

    # SocketIO Events
    @socketio.on('connect')
    def handle_connect():
        emit('status_update', _get_full_status())

    @socketio.on('request_update')
    def handle_request_update():
        emit('status_update', _get_full_status())

    @socketio.on('test_chat')
    def handle_test_chat(data):
        message = data.get('message', '')
        if not message:
            emit('test_chat_response', {'error': 'Message is empty'})
            return

        config = load_config()
        # Default to openai provider if available, or try to find one
        provider_config = config.get('providers', {}).get('openai', {})
        api_base = provider_config.get('apiBase')
        api_key = provider_config.get('apiKey', 'dummy')
        
        # Get model from defaults
        model = config.get('agents', {}).get('defaults', {}).get('model', 'gpt-3.5-turbo')

        if not api_base:
             emit('test_chat_response', {'error': 'No OpenAI provider configured'})
             return
             
        try:
            # Simple Chat Completion
            url = f"{api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": message}]
            }
            
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                rdata = resp.json()
                content = rdata['choices'][0]['message']['content']
                emit('test_chat_response', {'content': content})
            else:
                emit('test_chat_response', {'error': f"API Error: {resp.status_code} - {resp.text}"})
        except Exception as e:
            emit('test_chat_response', {'error': f"Request Failed: {str(e)}"})

    # Background Task for Push Updates
    def background_thread():
        while True:
            socketio.sleep(2) # Update every 2 seconds
            try:
                data = _get_full_status()
                socketio.emit('status_update', data)
            except Exception as e:
                print(f"Broadcast error: {e}")

    socketio.start_background_task(target=background_thread)

    def _get_full_status():
        sys_stats = monitor_service.get_system_stats()
        sess_data = session_service.get_sessions()
        tail_data = monitor_service.get_tailscale_status()
        cron_data = monitor_service.get_cron_jobs()
        gw_running = process_service.is_running()
        config_data = load_config()
        
        # Extract model for easier access
        model_name = config_data.get('agents', {}).get('defaults', {}).get('model', 'Unknown')
        if config_data:
            # Inject model at root of config for backward compatibility/easier access
            config_data['model'] = model_name

        return {
            "process": sys_stats,
            "sessions": sess_data,
            "tailscale": tail_data,
            "cron_jobs": cron_data,
            "gateway": {
                "running": gw_running,
                "status": "Running" if gw_running else "Stopped"
            },
            "config": config_data,
            "app_info": {
                "version": VERSION,
                "last_updated": LAST_UPDATED
            }
        }

    return app, socketio
