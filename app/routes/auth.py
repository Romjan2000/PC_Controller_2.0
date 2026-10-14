from flask import Blueprint, request, jsonify
from app.security import verify_plain_password, login_user, logout_user, is_authenticated

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    password = data.get('password', '')
    if verify_plain_password(password):
        token = login_user()
        return jsonify({
            'status': 'ok',
            'message': 'Login successful',
            'token': token
        })
    return jsonify({
        'status': 'error',
        'message': 'Invalid access key'
    }), 401

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    logout_user()
    return jsonify({'status': 'ok', 'message': 'Logged out'})

@auth_bp.route('/api/auth/check', methods=['GET'])
def api_check():
    return jsonify({'authenticated': is_authenticated()})
