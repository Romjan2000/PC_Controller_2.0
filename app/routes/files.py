import os
import shutil
from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from app import config
from app.security import require_auth, safe_resolve_path

files_bp = Blueprint('files', __name__)

@files_bp.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    if 'file' in request.files and request.files['file'].filename:
        f = request.files['file']
        filename = secure_filename(f.filename)
        if not filename:
            return jsonify({'status': 'invalid filename'}), 400
        save_path = os.path.join(config.UPLOAD_FOLDER, filename)
        f.save(save_path)
        return jsonify({'status': 'uploaded', 'filename': filename})
    return jsonify({'status': 'no file'}), 400

@files_bp.route('/api/files_list', methods=['GET'])
@require_auth
def list_files():
    try:
        files = [
            f for f in os.listdir(config.UPLOAD_FOLDER)
            if os.path.isfile(os.path.join(config.UPLOAD_FOLDER, f))
        ]
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files_bp.route('/api/files_download/<filename>')
@require_auth
def download_file(filename):
    clean_name = secure_filename(filename)
    return send_from_directory(config.UPLOAD_FOLDER, clean_name, as_attachment=True)

@files_bp.route('/api/browse')
@require_auth
def browse_files():
    req_path = request.args.get('path', os.path.expanduser('~'))
    resolved_path = safe_resolve_path(req_path)
    
    if not resolved_path:
        return jsonify({'status': 'error', 'message': 'Invalid or inaccessible path'}), 400
    
    try:
        items = []
        for item in os.listdir(resolved_path):
            item_path = os.path.join(resolved_path, item)
            try:
                is_dir = os.path.isdir(item_path)
                size = 0 if is_dir else os.path.getsize(item_path)
                items.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': is_dir,
                    'size': size
                })
            except Exception:
                continue
                
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        return jsonify({
            'status': 'ok',
            'path': resolved_path,
            'parent': os.path.dirname(resolved_path),
            'items': items[:100]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@files_bp.route('/api/open_file', methods=['POST'])
@require_auth
def open_file():
    data = request.get_json(silent=True) or {}
    resolved_path = safe_resolve_path(data.get('path', ''))
    if not resolved_path:
        return jsonify({'status': 'error', 'message': 'Invalid path'}), 400
    try:
        os.startfile(resolved_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@files_bp.route('/api/delete_file', methods=['POST'])
@require_auth
def delete_file():
    data = request.get_json(silent=True) or {}
    resolved_path = safe_resolve_path(data.get('path', ''))
    if not resolved_path:
        return jsonify({'status': 'error', 'message': 'Invalid path'}), 400
    
    # Critical security protection: prevent deleting root or system directory
    root_paths = [os.path.abspath(os.sep)]
    if os.name == 'nt':
        import string
        root_paths += [f"{d}:\\" for d in string.ascii_uppercase]
        root_paths += [os.environ.get('SystemRoot', 'C:\\Windows')]
        
    for r in root_paths:
        if resolved_path.lower() == r.lower():
            return jsonify({'status': 'error', 'message': 'Cannot delete root or system path'}), 403
            
    try:
        if os.path.isdir(resolved_path):
            shutil.rmtree(resolved_path)
        else:
            os.remove(resolved_path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
