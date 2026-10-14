import pyautogui
from flask import session
from flask_socketio import emit

# Shared mouse lock flag reference
from app.routes.control import mouse_locked

def register_socket_handlers(socketio):
    """Register WebSocket event handlers for ultra-low-latency controls."""

    @socketio.on('connect')
    def handle_connect():
        # Authenticated users get verified
        is_auth = session.get('authenticated', False)
        emit('connection_response', {'status': 'connected', 'authenticated': is_auth})

    @socketio.on('mouse_rel')
    def handle_mouse_rel(data):
        """Relative cursor delta (x, y) with sub-15ms response time."""
        if not mouse_locked:
            dx = int(data.get('x', 0))
            dy = int(data.get('y', 0))
            pyautogui.moveRel(dx, dy)

    @socketio.on('mouse_click')
    def handle_mouse_click(data):
        """Instant mouse click."""
        if not mouse_locked:
            button = data.get('btn', 'left')
            pyautogui.click(button=button)

    @socketio.on('ghost_type')
    def handle_ghost_type(data):
        """Instant remote keystroke injection."""
        text = data.get('text', '')
        if text:
            pyautogui.write(text, interval=0.03)

    @socketio.on('ping_check')
    def handle_ping(data):
        """Instant latency calculation."""
        emit('pong_reply', data)
