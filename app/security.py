import os
import hashlib
import secrets
from functools import wraps
from pathlib import Path
from flask import session, request, jsonify
from app import config

# Store active API session tokens in memory
ACTIVE_API_TOKENS = set()

def verify_password(input_pwd):
    """Timing-safe verification of the admin password hash."""
    if not input_pwd:
        return False
    computed_hash = hashlib.sha256(input_pwd.encode('utf-8')).hexdigest()
    return secrets.compare_digest(computed_hash, config.APP_PASSWORD_HASH)

def verify_plain_password(input_pwd):
    """Timing-safe verification of UI login password."""
    if not input_pwd:
        return False
    return secrets.compare_digest(str(input_pwd), str(config.UI_PASSWORD))

def is_authenticated():
    """Check if the current request is authenticated via session or Authorization header."""
    # 1. Check Flask signed session
    if session.get('authenticated') is True:
        return True
    
    # 2. Check Bearer Token in header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
        if token and token in ACTIVE_API_TOKENS:
            return True
            
    return False

def login_user():
    """Mark session as authenticated and return an API token."""
    session['authenticated'] = True
    session.permanent = True
    token = secrets.token_hex(24)
    ACTIVE_API_TOKENS.add(token)
    return token

def logout_user():
    """Clear user session."""
    session.pop('authenticated', None)

def require_auth(f):
    """Decorator to protect API endpoints against unauthorized access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({
                'status': 'unauthorized',
                'message': 'Authentication required. Please log in.'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def safe_resolve_path(target_path):
    """
    Sanitize and resolve a user-supplied filesystem path.
    Prevents path traversal exploits (e.g. ../../) and invalid characters.
    """
    if not target_path or not isinstance(target_path, str):
        return None
    try:
        resolved = Path(target_path).resolve()
        # Verify path exists
        if not resolved.exists():
            return None
        return str(resolved)
    except Exception:
        return None
