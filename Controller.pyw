"""
PC Controller 2.0 - Main Launcher
Modular, Secured, and Low-Latency Remote PC Management System
"""
import os
import sys
import threading
from app import create_app, socketio, config
from app.services.tunnel import start_tunnel

# Auto-updater
try:
    from updater import start_update_checker
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("  🖥️  PC CONTROLLER 2.0 (MODULAR & SECURED)")
    print(f"  Version: v{config.APP_VERSION}")
    print(f"  Local Port: {config.PORT}")
    print("=" * 60)

    # 1. Start tunnel thread in background
    tunnel_thread = threading.Thread(target=start_tunnel, daemon=True)
    tunnel_thread.start()

    # 2. Start auto-updater if enabled
    if UPDATER_AVAILABLE and os.getenv('AUTO_UPDATE', 'true').lower() == 'true':
        start_update_checker()

    # 3. Start high-performance WebSocket & HTTP server
    print(f"[PC Controller] Server ready on http://localhost:{config.PORT}")
    socketio.run(
        app,
        host='0.0.0.0',
        port=config.PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )