import os
import io
import json
import base64
import subprocess
import pyautogui
from flask import Blueprint, request, jsonify
from app import config
from app.security import require_auth

apps_bp = Blueprint('apps', __name__)
APPS_CONFIG_FILE = os.path.join(config.BASE_DIR, 'apps.json')

def load_apps():
    if os.path.exists(APPS_CONFIG_FILE):
        try:
            with open(APPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except Exception:
            return []
    return []

def save_apps(apps):
    with open(APPS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(apps, f, indent=2)

@apps_bp.route('/api/apps')
@require_auth
def list_apps():
    return jsonify({'status': 'ok', 'apps': load_apps()})

@apps_bp.route('/api/launch_app', methods=['POST'])
@require_auth
def launch_app():
    data = request.get_json(silent=True) or {}
    path = data.get('path')
    try:
        subprocess.Popen(path, shell=True)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@apps_bp.route('/api/add_app', methods=['POST'])
@require_auth
def add_app():
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    path = data.get('path')
    icon = data.get('icon', '')
    
    if not name or not path:
        return jsonify({'status': 'error', 'message': 'Missing name or path'}), 400
        
    apps = load_apps()
    apps.append({'name': name, 'path': path, 'icon': icon})
    save_apps(apps)
    return jsonify({'status': 'ok'})

@apps_bp.route('/api/remove_app', methods=['POST'])
@require_auth
def remove_app():
    data = request.get_json(silent=True) or {}
    path = data.get('path')
    apps = load_apps()
    apps = [a for a in apps if a.get('path') != path]
    save_apps(apps)
    return jsonify({'status': 'ok'})

@apps_bp.route('/api/extract_icon', methods=['POST'])
@require_auth
def extract_icon():
    data = request.get_json(silent=True) or {}
    path = data.get('path', '')
    if not path.lower().endswith('.exe') or not os.path.exists(path):
        return jsonify({'status': 'error', 'message': 'Invalid exe path'}), 400
        
    try:
        from PIL import Image
        import win32ui
        import win32gui
        import win32con
        import win32api
        
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        large, small = win32gui.ExtractIconEx(path, 0)
        
        if large:
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_x)
            hdc2 = hdc.CreateCompatibleDC()
            hdc2.SelectObject(hbmp)
            hdc2.DrawIcon((0, 0), large[0])
            
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            icon_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            win32gui.DestroyIcon(large[0])
            if small:
                win32gui.DestroyIcon(small[0])
            return jsonify({'status': 'ok', 'icon': f'data:image/png;base64,{icon_b64}'})
    except Exception:
        pass
    return jsonify({'status': 'error', 'message': 'Could not extract icon'})

@apps_bp.route('/api/voice_command', methods=['POST'])
@require_auth
def voice_command():
    try:
        data = request.get_json(silent=True) or {}
        command = data.get('command', '').lower()
        
        app_commands = {
            'chrome': 'start chrome', 'ক্রোম': 'start chrome',
            'notepad': 'notepad', 'নোটপ্যাড': 'notepad',
            'calculator': 'calc', 'ক্যালকুলেটর': 'calc',
            'explorer': 'explorer', 'এক্সপ্লোরার': 'explorer',
            'discord': 'start discord', 'ডিসকর্ড': 'start discord',
            'spotify': 'start spotify', 'স্পটিফাই': 'start spotify',
            'browser': 'start chrome', 'ব্রাউজার': 'start chrome',
            'task manager': 'taskmgr', 'টাস্ক ম্যানেজার': 'taskmgr',
            'settings': 'start ms-settings:', 'সেটিংস': 'start ms-settings:',
        }
        
        # Volume
        if any(w in command for w in ['volume up', 'ভলিউম আপ', 'আওয়াজ বাড়াও']):
            for _ in range(3): pyautogui.press('volumeup')
            return jsonify({'status': 'ok', 'action': 'volume_up'})
        if any(w in command for w in ['volume down', 'ভলিউম ডাউন', 'আওয়াজ কমাও']):
            for _ in range(3): pyautogui.press('volumedown')
            return jsonify({'status': 'ok', 'action': 'volume_down'})
        if any(w in command for w in ['mute', 'মিউট']):
            pyautogui.press('volumemute')
            return jsonify({'status': 'ok', 'action': 'mute'})
            
        # Media
        if any(w in command for w in ['play', 'pause', 'প্লে', 'পজ']):
            pyautogui.press('playpause')
            return jsonify({'status': 'ok', 'action': 'playpause'})
        if any(w in command for w in ['next', 'skip', 'নেক্সট', 'স্কিপ']):
            pyautogui.press('nexttrack')
            return jsonify({'status': 'ok', 'action': 'next'})
        if any(w in command for w in ['previous', 'back', 'আগের']):
            pyautogui.press('prevtrack')
            return jsonify({'status': 'ok', 'action': 'previous'})
            
        # Predefined apps
        for app_name, app_cmd in app_commands.items():
            if app_name in command:
                subprocess.Popen(app_cmd, shell=True)
                return jsonify({'status': 'ok', 'action': f'opened_{app_name}'})
                
        # Open prefix
        if command.startswith('open ') or command.startswith('ওপেন '):
            app_name = command.replace('open ', '').replace('ওপেন ', '').strip()
            subprocess.Popen(f'start {app_name}', shell=True)
            return jsonify({'status': 'ok', 'action': f'opened_{app_name}'})
            
        # Power commands
        if any(w in command for w in ['shutdown', 'শাটডাউন', 'বন্ধ করো']):
            return jsonify({'status': 'confirm', 'action': 'shutdown', 'message': 'Confirm shutdown?'})
        if any(w in command for w in ['restart', 'রিস্টার্ট']):
            return jsonify({'status': 'confirm', 'action': 'restart', 'message': 'Confirm restart?'})
        if any(w in command for w in ['sleep', 'ঘুমাও', 'স্লিপ']):
            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            return jsonify({'status': 'ok', 'action': 'sleep'})
        if any(w in command for w in ['lock', 'লক']):
            os.system('rundll32.exe user32.dll,LockWorkStation')
            return jsonify({'status': 'ok', 'action': 'lock'})
            
        return jsonify({'status': 'unknown', 'message': 'Command not recognized'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
