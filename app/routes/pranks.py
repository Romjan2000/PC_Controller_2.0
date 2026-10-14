import os
import sys
import time
import subprocess
import threading
import psutil
import pyautogui
from flask import Blueprint, request, jsonify
from app import config
from app.security import require_auth

pranks_bp = Blueprint('pranks', __name__)

active_pranks = {}
matrix_display_proc = None

@pranks_bp.route('/api/prank', methods=['POST'])
@require_auth
def run_prank():
    global active_pranks
    data = request.get_json(silent=True) or {}
    action = data.get('action')
    state = data.get('state')
    speed = data.get('speed', 'NORMAL')
    color = data.get('color', 'green')
    length = data.get('length', 'medium')
    
    script_map = {
        'hacker': 'hacker_prank.py',
        'bsod': 'bsod_prank.py',
        'matrix': 'matrix_rain.py',
        'crazy_mouse': 'crazy_mouse.py',
        'random_sounds': 'random_sounds.py'
    }
    
    if action in script_map:
        if state == 'on' and action not in active_pranks:
            script_path = config.get_script_path(script_map[action])
            if os.path.exists(script_path):
                if action == 'matrix':
                    proc = subprocess.Popen([sys.executable, script_path, speed, color, length], creationflags=0x00000008, close_fds=True)
                else:
                    proc = subprocess.Popen([sys.executable, script_path, speed], creationflags=0x00000008, close_fds=True)
                active_pranks[action] = proc
        elif state == 'off' and action in active_pranks:
            try:
                parent = psutil.Process(active_pranks[action].pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except Exception:
                pass
            finally:
                if action in active_pranks:
                    del active_pranks[action]
        return jsonify({'status': 'toggled'})
    
    if action == 'jiggle':
        def jiggle_loop():
            for _ in range(20):
                pyautogui.moveRel(10, 10)
                time.sleep(0.1)
                pyautogui.moveRel(-10, -10)
                time.sleep(0.1)
        threading.Thread(target=jiggle_loop).start()
        return jsonify({'status': 'jiggling'})
        
    if action == 'cd_eject':
        subprocess.Popen([sys.executable, config.get_script_path('cd_tray.py'), 'eject'], creationflags=0x00000008)
        return jsonify({'status': 'ejected'})
        
    if action == 'cd_close':
        subprocess.Popen([sys.executable, config.get_script_path('cd_tray.py'), 'close'], creationflags=0x00000008)
        return jsonify({'status': 'closed'})
        
    if action == 'cd_disco':
        subprocess.Popen([sys.executable, config.get_script_path('cd_tray.py'), 'disco', '5'], creationflags=0x00000008)
        return jsonify({'status': 'disco'})
        
    if action == 'scary':
        subprocess.Popen([sys.executable, config.get_script_path('scary_popup.py')], creationflags=0x00000008)
        return jsonify({'status': 'scared'})
        
    return jsonify({'status': 'unknown'})

@pranks_bp.route('/api/note_popup', methods=['POST'])
@require_auth
def note_popup():
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    subprocess.Popen([sys.executable, config.get_script_path('note_popup.py'), text], creationflags=0x00000008)
    return jsonify({'status': 'sent'})

@pranks_bp.route('/api/matrix_image', methods=['POST'])
@require_auth
def matrix_image():
    global matrix_display_proc
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'status': 'no file'})
    
    try:
        if matrix_display_proc and matrix_display_proc.poll() is None:
            matrix_display_proc.terminate()
    except Exception:
        pass
        
    f = request.files['file']
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), 'matrix_img_temp.png')
    f.save(temp_path)
    
    matrix_display_proc = subprocess.Popen([sys.executable, config.get_script_path('matrix_image.py'), temp_path], creationflags=0x00000008)
    return jsonify({'status': 'displaying'})

@pranks_bp.route('/api/matrix_close', methods=['POST'])
@require_auth
def matrix_close():
    global matrix_display_proc
    try:
        if matrix_display_proc and matrix_display_proc.poll() is None:
            matrix_display_proc.terminate()
            matrix_display_proc = None
            return jsonify({'status': 'closed'})
    except Exception:
        pass
    return jsonify({'status': 'not_running'})
