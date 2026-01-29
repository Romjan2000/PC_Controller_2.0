import os
import sys
import time
import threading
import base64
import io
import random
import win32gui
import psutil
import pyautogui
import pyttsx3
import pyperclip
import subprocess
import requests
import hashlib
import webbrowser
from flask import Flask, render_template_string, request, jsonify, send_from_directory, Response
from PIL import Image
from dotenv import load_dotenv

# Auto-update system
try:
    from updater import start_update_checker, manual_check, get_local_version
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    def get_local_version(): return 'unknown'

# --- LOAD CONFIGURATION ---
load_dotenv()

# --- CONFIGURATION & SECURITY ---
PORT = int(os.getenv('PORT', 1010))

# 1. UI Password (Reads Plain Text from .env)
UI_PASSWORD = os.getenv('APP_PASSWORD_PLAIN', '1122')

# 2. Server Hash (Reads Hash from .env)
APP_PASSWORD_HASH = os.getenv('APP_PASSWORD_HASH', 'd05ad294422e1e6f4b6a1e7f9b8f0e7e9a1d5e1e3d2b8c6a1e5e9d4f3b2a1c0')

def verify_password(input_pwd):
    return hashlib.sha256(input_pwd.encode()).hexdigest() == APP_PASSWORD_HASH

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "REPLACE_ME")
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', "REPLACE_ME")
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE_MB', 1024)) * 1024 * 1024 

try:
    user_profile = os.environ['USERPROFILE']
    DOWNLOADS_FOLDER = os.path.join(user_profile, 'Downloads')
except:
    DOWNLOADS_FOLDER = os.path.expanduser('~/Downloads')

UPLOAD_FOLDER = DOWNLOADS_FOLDER
if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

active_pranks = {} 
mouse_locked = False

# Load version
APP_VERSION = get_local_version()
print(f"[PC Controller] Version {APP_VERSION}")

# --- HELPERS ---
def get_script_path(script_name):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'scripts', script_name)

def send_telegram_message(message):
    if TELEGRAM_BOT_TOKEN == "REPLACE_ME": return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except: pass

def start_tunnel_thread():
    """Start tunnel using Cloudflare (preferred) or fallback to ngrok"""
    public_url = None
    
    # Try Cloudflare Tunnel first (free, unlimited, no account needed)
    try:
        cloudflared_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloudflared.exe')
        if not os.path.exists(cloudflared_path):
            cloudflared_path = 'cloudflared'  # Try system PATH
        
        # Start cloudflared with TryCloudflare (no account needed)
        process = subprocess.Popen(
            [cloudflared_path, 'tunnel', '--url', f'http://localhost:{PORT}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        
        # Wait for the tunnel URL
        import re
        for _ in range(30):  # Wait up to 30 seconds
            line = process.stdout.readline()
            if line:
                # Look for the trycloudflare URL
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    public_url = match.group(1)
                    print(f"[CLOUDFLARE] Tunnel LIVE: {public_url}")
                    send_telegram_message(f"🚀 PC CONTROLLER STARTED\n🌐 Cloudflare Tunnel\nLink: {public_url}")
                    return
            time.sleep(1)
    except FileNotFoundError:
        print("[INFO] Cloudflared not found, trying ngrok...")
    except Exception as e:
        print(f"[WARN] Cloudflare tunnel error: {e}, trying ngrok...")
    
    # Fallback to ngrok
    try:
        ngrok_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ngrok.exe')
        if not os.path.exists(ngrok_path):
            ngrok_path = 'ngrok'
        subprocess.Popen([ngrok_path, 'http', str(PORT)], creationflags=0x08000000)
        time.sleep(3)
        for _ in range(10):
            try:
                public_url = requests.get("http://127.0.0.1:4040/api/tunnels").json()['tunnels'][0]['public_url']
                print(f"[NGROK] Tunnel LIVE: {public_url}")
                send_telegram_message(f"🚀 PC CONTROLLER STARTED\n📡 Ngrok Tunnel\nLink: {public_url}")
                return
            except: time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Ngrok tunnel error: {e}")
    
    # No tunnel available - local only
    print(f"[WARN] No tunnel available. Access locally at: http://localhost:{PORT}")
    send_telegram_message(f"⚠️ PC Controller started (LOCAL ONLY)\nNo tunnel available\nLocal: http://localhost:{PORT}")

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(HTML_UI)

@app.route('/api/status')
def get_status():
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        try:
            hwnd = win32gui.GetForegroundWindow()
            app_name = win32gui.GetWindowText(hwnd)
        except: app_name = "Unknown"
        return jsonify({'app': app_name, 'cpu': cpu, 'ram': ram, 'mouse_locked': mouse_locked})
    except: return jsonify({'app': 'Error', 'cpu': 0, 'ram': 0, 'mouse_locked': False})

@app.route('/api/screenshot')
def screenshot():
    try:
        screenshot = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='JPEG', quality=85)
        img_byte_arr = img_byte_arr.getvalue()
        return jsonify({'img': base64.b64encode(img_byte_arr).decode('utf-8')})
    except: return jsonify({'img': None})

# --- NEW FEATURE: LIVE STREAM (MJPEG) ---
@app.route('/api/live_stream')
def live_stream():
    def generate():
        try:
            while True:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=40) 
                frame = buf.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.05)  # ~20 FPS cap to reduce CPU load
        except GeneratorExit:
            pass
        except Exception as e:
            print(f"Stream Error: {e}")
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/mouse_click', methods=['POST'])
def mouse_click():
    data = request.json
    if not mouse_locked: pyautogui.click(button=data.get('btn', 'left'))
    return jsonify({'status': 'success'})

@app.route('/api/mouse_rel', methods=['POST'])
def mouse_rel():
    data = request.json
    if not mouse_locked: pyautogui.moveRel(int(data.get('x', 0)), int(data.get('y', 0)))
    return jsonify({'status': 'success'})

@app.route('/api/ghost_type', methods=['POST'])
def ghost_type():
    pyautogui.write(request.json.get('text', ''), interval=0.05)
    return jsonify({'status': 'success'})

@app.route('/api/speak', methods=['POST'])
def speak():
    text_to_speak = request.json.get('text', '')
    def run_speech():
        try:
            engine = pyttsx3.init()
            engine.say(text_to_speak)
            engine.runAndWait()
        except: pass
    threading.Thread(target=run_speech).start()
    return jsonify({'status': 'speaking'})

@app.route('/api/clipboard_get', methods=['GET'])
def clipboard_get():
    try: return jsonify({'text': pyperclip.paste()})
    except: return jsonify({'text': ''})

@app.route('/api/clipboard_send', methods=['POST'])
def clipboard_send():
    pyperclip.copy(request.json.get('text', ''))
    return jsonify({'status': 'copied'})

@app.route('/api/prank', methods=['POST'])
def run_prank():
    data = request.json
    action, state, speed = data.get('action'), data.get('state'), data.get('speed', 'NORMAL')
    script_map = {'hacker': 'hacker_prank.py', 'bsod': 'bsod_prank.py', 'matrix': 'matrix_rain.py'}
    
    if action in script_map:
        if state == 'on' and action not in active_pranks:
            script_path = get_script_path(script_map[action])
            if os.path.exists(script_path):
                proc = subprocess.Popen([sys.executable, script_path, speed], creationflags=0x00000008, close_fds=True)
                active_pranks[action] = proc
        elif state == 'off' and action in active_pranks:
            try:
                parent = psutil.Process(active_pranks[action].pid)
                for child in parent.children(recursive=True): child.kill()
                parent.kill()
            except: pass
            finally:
                if action in active_pranks: del active_pranks[action]
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
    return jsonify({'status': 'unknown'})

@app.route('/api/note_popup', methods=['POST'])
def note_popup():
    subprocess.Popen([sys.executable, get_script_path('note_popup.py'), request.json.get('text', '')], creationflags=0x00000008)
    return jsonify({'status': 'sent'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' in request.files and request.files['file'].filename:
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        return jsonify({'status': 'uploaded', 'filename': f.filename})
    return jsonify({'status': 'no file'})

@app.route('/api/files_list', methods=['GET'])
def list_files():
    return jsonify([f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))])

@app.route('/api/files_download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/api/action', methods=['POST'])
def system_action():
    if verify_password(request.json.get('password')):
        act = request.json.get('action')
        if act == 'shutdown': os.system("shutdown /s /t 0")
        elif act == 'restart': os.system("shutdown /r /t 0")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'wrong password'})

@app.route('/api/exec', methods=['POST'])
def exec_command():
    if verify_password(request.json.get('password')):
        try:
            out = subprocess.check_output(request.json.get('cmd'), shell=True, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            return jsonify({'status': 'success', 'output': out.decode('cp437', errors='ignore')})
        except Exception as e: return jsonify({'status': 'error', 'output': str(e)})
    return jsonify({'status': 'unauthorized'})

@app.route('/api/open_url', methods=['POST'])
def open_url():
    webbrowser.open(request.json.get('url'))
    return jsonify({'status': 'opened'})

@app.route('/api/version')
def get_version():
    return jsonify({'version': APP_VERSION, 'updater_available': UPDATER_AVAILABLE})

@app.route('/api/check_update', methods=['POST'])
def check_update():
    if UPDATER_AVAILABLE:
        updated = manual_check()
        return jsonify({'status': 'checked', 'updated': updated})
    return jsonify({'status': 'updater_not_available'})

@app.route('/api/media', methods=['POST'])
def media_control():
    global mouse_locked
    act = request.json.get('action')
    if act == 'playpause': pyautogui.press('playpause')
    elif act == 'next': pyautogui.press('nexttrack')
    elif act == 'prev': pyautogui.press('prevtrack')
    elif act == 'lock_mouse': mouse_locked = not mouse_locked
    return jsonify({'status': 'ok'})

# --- NEW: Volume Control ---
@app.route('/api/volume', methods=['POST'])
def volume_control():
    act = request.json.get('action')
    if act == 'up': pyautogui.press('volumeup')
    elif act == 'down': pyautogui.press('volumedown')
    elif act == 'mute': pyautogui.press('volumemute')
    return jsonify({'status': 'ok'})

# --- NEW: Power Actions ---
@app.route('/api/power', methods=['POST'])
def power_control():
    act = request.json.get('action')
    if verify_password(request.json.get('password', '')):
        if act == 'sleep': 
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif act == 'lock': 
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif act == 'logoff':
            os.system("shutdown /l")
        return jsonify({'status': 'success'})
    # Lock doesn't need password
    if act == 'lock':
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'wrong password'})

# --- NEW: Keyboard Shortcuts ---
@app.route('/api/hotkey', methods=['POST'])
def keyboard_hotkey():
    act = request.json.get('action')
    if act == 'alt_tab': pyautogui.hotkey('alt', 'tab')
    elif act == 'win_d': pyautogui.hotkey('win', 'd')  # Show desktop
    elif act == 'alt_f4': pyautogui.hotkey('alt', 'F4')  # Close window
    elif act == 'win_l': pyautogui.hotkey('win', 'l')  # Lock
    elif act == 'win_e': pyautogui.hotkey('win', 'e')  # File explorer
    elif act == 'ctrl_shift_esc': pyautogui.hotkey('ctrl', 'shift', 'esc')  # Task manager
    elif act == 'print_screen': pyautogui.press('printscreen')
    elif act == 'escape': pyautogui.press('escape')
    elif act == 'enter': pyautogui.press('enter')
    elif act == 'backspace': pyautogui.press('backspace')
    elif act == 'space': pyautogui.press('space')
    return jsonify({'status': 'ok'})

# --- NEW: System Information ---
@app.route('/api/sysinfo')
def system_info():
    try:
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = time.time() - psutil.boot_time()
        
        # Convert uptime to readable format
        days = int(boot_time // 86400)
        hours = int((boot_time % 86400) // 3600)
        minutes = int((boot_time % 3600) // 60)
        uptime_str = f"{days}d {hours}h {minutes}m"
        
        return jsonify({
            'cpu_cores': cpu_count,
            'cpu_freq_mhz': round(cpu_freq.current) if cpu_freq else 0,
            'ram_total_gb': round(mem.total / (1024**3), 1),
            'ram_used_gb': round(mem.used / (1024**3), 1),
            'disk_total_gb': round(disk.total / (1024**3), 1),
            'disk_used_gb': round(disk.used / (1024**3), 1),
            'uptime': uptime_str,
            'version': APP_VERSION
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# --- PREMIUM UI HTML ---
# NOTE: The 'f' before """ allows us to use {UI_PASSWORD} inside the HTML
HTML_UI = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>PC CONTROL PRO</title>
    <style>
        :root {{
            --bg: #09090b; --surface: #18181b; --surface-light: #27272a;
            --primary: #8b5cf6; --primary-glow: rgba(139, 92, 246, 0.5);
            --accent: #06b6d4; --danger: #f43f5e;
            --text-main: #f4f4f5; --text-muted: #a1a1aa;
            --border: rgba(255, 255, 255, 0.08);
            --glass: rgba(24, 24, 27, 0.7);
        }}
        * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background: var(--bg); color: var(--text-main); margin: 0; padding: 0; padding-bottom: 100px; 
            background-image: radial-gradient(circle at 50% 0%, #2e1065 0%, transparent 50%), radial-gradient(circle at 0% 100%, #0e7490 0%, transparent 40%);
            background-attachment: fixed;
        }}
        
        /* --- LOGIN OVERLAY --- */
        #login-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(20px); z-index: 2000; display: flex; align-items: center; justify-content: center; }}
        .login-card {{ background: var(--surface); border: 1px solid var(--border); padding: 40px; border-radius: 32px; width: 90%; max-width: 320px; text-align: center; box-shadow: 0 20px 50px -10px rgba(0,0,0,0.5); }}
        .brand-title {{ font-size: 26px; font-weight: 800; background: linear-gradient(to right, #c4b5fd, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 30px; letter-spacing: -0.5px; }}
        
        /* --- GENERAL INPUTS --- */
        input, textarea {{ width: 100%; background: var(--surface-light); border: 1px solid var(--border); color: white; padding: 16px; border-radius: 16px; margin-bottom: 15px; font-size: 15px; transition: 0.2s; font-family: 'Courier New', monospace; }}
        input:focus, textarea:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15); background: #27272a; }}
        select.speed-select {{ width: 100%; background: var(--surface-light); border: 1px solid var(--border); color: var(--text-muted); padding: 12px; border-radius: 12px; margin-top: 10px; font-size: 13px; appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 12px center; background-size: 16px; }}
        
        /* --- LAYOUT & CARDS --- */
        .container {{ padding: 24px; max-width: 600px; margin: 0 auto; }}
        .header {{ margin-bottom: 28px; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ margin: 4px 0 0; color: var(--text-muted); font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        .tab-content {{ display: none; animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }}
        .tab-content.active {{ display: block; }}
        @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(15px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        
        .card {{ background: var(--glass); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 24px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); transition: transform 0.2s; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .card-title {{ font-size: 13px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
        
        /* --- BUTTONS --- */
        .btn {{ width: 100%; padding: 16px; border-radius: 16px; border: none; font-weight: 600; font-size: 15px; cursor: pointer; transition: 0.2s cubic-bezier(0.16, 1, 0.3, 1); display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 12px; position: relative; overflow: hidden; }}
        .btn-primary {{ background: linear-gradient(135deg, var(--primary), #7c3aed); color: white; box-shadow: 0 8px 16px rgba(124, 58, 237, 0.2); }}
        .btn-primary:active {{ transform: scale(0.96); }}
        .btn-danger {{ background: rgba(244, 63, 94, 0.1); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.2); }}
        .btn-ghost {{ background: rgba(255, 255, 255, 0.05); color: var(--text-main); border: 1px solid var(--border); }}
        .btn-ghost:active {{ background: rgba(255,255,255,0.1); }}
        
        /* --- STATS --- */
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .stat-card {{ background: linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%); border: 1px solid var(--border); border-radius: 20px; padding: 20px; text-align: center; position: relative; }}
        .stat-circle {{ width: 90px; height: 90px; margin: 0 auto 15px; border-radius: 50%; background: conic-gradient(var(--primary) 0%, rgba(255,255,255,0.05) 0%); display: flex; align-items: center; justify-content: center; position: relative; box-shadow: 0 0 20px var(--primary-glow); }}
        .stat-inner {{ width: 72px; height: 72px; background: #121214; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 18px; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); font-weight: 600; letter-spacing: 0.5px; }}
        
        /* --- SCREENSHOT & LIVE STREAM --- */
        .screen-preview {{ width: 100%; height: 220px; background: #000; border-radius: 20px; overflow: hidden; position: relative; border: 1px solid var(--border); box-shadow: inset 0 0 30px rgba(0,0,0,0.5); }}
        .screen-preview img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s; }}
        .screen-preview img.loaded {{ opacity: 1; }}
        
        /* LIVE MODE SPECIFIC */
        .screen-preview img.live {{ object-fit: contain; opacity: 1; }} /* Always visible in live mode */
        .live-badge {{ position: absolute; top: 12px; left: 12px; background: rgba(220, 38, 38, 0.9); color: white; padding: 4px 10px; border-radius: 6px; font-size: 10px; font-weight: 800; letter-spacing: 1px; display: none; z-index: 10; animation: pulse 1.5s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}

        .screen-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.8)); color: white; font-weight: 600; font-size: 14px; letter-spacing: 1px; gap: 10px; z-index: 5; transition: opacity 0.3s; cursor: pointer; }}
        .screen-preview:hover .screen-overlay {{ opacity: 1; }}
        .screen-preview.live-mode .screen-overlay {{ opacity: 0; pointer-events: none; }} /* Hide overlay in live mode */

        /* --- TRACKPAD --- */
        .trackpad {{ width: 100%; height: 300px; background: linear-gradient(135deg, #27272a 0%, #1f1f22 100%); border-radius: 24px; border: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-weight: 700; letter-spacing: 2px; position: relative; box-shadow: inset 0 2px 10px rgba(0,0,0,0.3); transition: border-color 0.3s; }}
        .trackpad:active {{ border-color: var(--primary); }}
        .trackpad::after {{ content: 'TOUCHPAD'; opacity: 0.3; font-size: 14px; }}

        /* --- TOGGLES --- */
        .toggle-row {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--border); }}
        .toggle-row:last-child {{ border-bottom: none; }}
        .toggle-label {{ font-weight: 600; font-size: 15px; color: var(--text-main); }}
        .switch {{ position: relative; display: inline-block; width: 48px; height: 28px; }}
        .switch input {{ opacity: 0; width: 0; height: 0; }}
        .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: var(--surface-light); border-radius: 34px; transition: .4s; border: 1px solid var(--border); }}
        .slider:before {{ position: absolute; content: ""; height: 22px; width: 22px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .4s; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        input:checked + .slider {{ background-color: var(--primary); border-color: var(--primary); }}
        input:checked + .slider:before {{ transform: translateX(20px); }}

        /* --- FILE LIST --- */
        .file-item {{ display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 16px; border-radius: 16px; margin-bottom: 10px; border: 1px solid var(--border); }}
        .file-icon {{ font-size: 22px; margin-right: 12px; }}
        .file-name {{ font-family: monospace; font-size: 14px; color: var(--text-main); }}
        .download-btn {{ background: var(--primary); color: white; padding: 8px 16px; border-radius: 10px; font-size: 12px; font-weight: 600; text-decoration: none; box-shadow: 0 4px 10px rgba(139, 92, 246, 0.3); }}

        /* --- BOTTOM NAV --- */
        .bottom-nav {{ position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 540px; background: rgba(24, 24, 27, 0.85); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.1); border-radius: 32px; display: flex; justify-content: space-around; padding: 12px; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.6); z-index: 1000; }}
        .nav-item {{ background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; padding: 12px; border-radius: 20px; transition: 0.3s; display: flex; flex-direction: column; align-items: center; gap: 4px; }}
        .nav-item span {{ font-size: 10px; font-weight: 600; }}
        .nav-item.active {{ color: var(--primary); background: rgba(139, 92, 246, 0.1); transform: translateY(-4px); }}
        .nav-item.active span {{ color: var(--primary); }}
        
        /* --- UTILS --- */
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .clip-box {{ background: #000; color: var(--accent); padding: 16px; border-radius: 16px; font-family: monospace; font-size: 13px; word-break: break-all; min-height: 60px; border: 1px solid var(--border); margin-bottom: 10px; position: relative; }}
        .clip-box::before {{ content: 'CLIPBOARD'; position: absolute; top: -8px; left: 10px; background: var(--bg); padding: 0 5px; font-size: 10px; color: var(--text-muted); font-weight: bold; }}
        
        .progress-container {{ margin-top: 15px; }}
        .progress-bg {{ background: var(--surface-light); border-radius: 10px; height: 8px; width: 100%; overflow: hidden; border: 1px solid var(--border); }}
        .progress-fill {{ background: linear-gradient(90deg, var(--primary), var(--accent)); height: 100%; width: 0%; transition: width 0.2s ease; border-radius: 10px; }}
    </style>
</head>
<body>
<div id="login-overlay"><div class="login-card"><div class="brand-title">AUTHENTICATE</div><input type="password" id="login-pwd" placeholder="Enter Access Key" onkeydown="if(event.key==='Enter') doLogin()"><button class="btn btn-primary" onclick="doLogin()">LOGIN</button></div></div>

<div class="container" id="main-app" style="display:none;">
    <div class="header">
        <div>
            <h1 id="page-title">Dashboard</h1>
            <p id="active-app">Connecting...</p>
        </div>
        <div style="width: 40px; height: 40px; background: var(--surface-light); border-radius: 12px; display:flex; align-items:center; justify-content:center; border: 1px solid var(--border);">
            <span style="font-size:20px;">🖥️</span>
        </div>
    </div>

    <!-- DASHBOARD TAB -->
    <div id="dash" class="tab-content active">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-circle"><div class="stat-inner" id="cpu-circle">0%</div></div>
                <div class="stat-label">CPU LOAD</div>
            </div>
            <div class="stat-card">
                <div class="stat-circle" style="--primary: #06b6d4; --primary-glow: rgba(6, 182, 212, 0.5)"><div class="stat-inner" id="ram-circle" style="color:#06b6d4">0%</div></div>
                <div class="stat-label">MEMORY</div>
            </div>
        </div>
        
        <div class="card" style="margin-top:24px">
            <div class="card-header">
                <span class="card-title">Remote Eye</span>
                <div class="toggle-row" style="border:none; padding:0;">
                    <span style="font-size:12px; font-weight:600; color:var(--text-muted);">LIVE MODE</span>
                    <label class="switch" style="transform:scale(0.8)">
                        <input type="checkbox" id="live-toggle" onchange="toggleLive(this)">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
            <div class="screen-preview" id="screen-container">
                <div class="live-badge" id="live-badge">● LIVE</div>
                <div class="screen-overlay" id="ss-overlay" onclick="shoot()">
                    <div style="font-size:24px;">📷</div>
                    TAP TO CAPTURE
                </div>
                <!-- Image source changes dynamically -->
                <img id="ss-img">
            </div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">System Control</span></div>
            <div class="grid-2">
                <button class="btn btn-ghost" onclick="doAction('restart')">↻ Reboot</button>
                <button class="btn btn-danger" onclick="doAction('shutdown')">⏻ Shutdown</button>
            </div>
            <div class="grid-2" style="margin-top:10px">
                <button class="btn btn-ghost" onclick="post('/api/power', {{action:'lock'}})">🔒 Lock PC</button>
                <button class="btn btn-ghost" onclick="doPower('sleep')">😴 Sleep</button>
            </div>
            <div style="margin-top: 15px; padding-top:15px; border-top:1px solid var(--border)">
                <input type="text" id="cmd-input" placeholder="CMD Command (e.g., calc)" style="margin-bottom:10px">
                <button class="btn btn-ghost" onclick="runCmd()" style="height: 50px;">▶ Run Command</button>
                <div id="cmd-out" style="font-family:monospace; font-size:12px; color:var(--text-muted); margin-top:10px; max-height:80px; overflow:auto; background:rgba(0,0,0,0.2); padding:10px; border-radius:10px; min-height:40px;"></div>
            </div>
        </div>
    </div>

    <!-- INPUT TAB -->
    <div id="input" class="tab-content">
        <div class="card">
            <div class="card-header"><span class="card-title">Input Device</span></div>
            <div class="trackpad" id="pad"></div>
            <div class="grid-2" style="margin-top: 20px;">
                <button class="btn btn-ghost" onclick="post('/api/mouse_click', {{btn:'left'}})">Left Click</button>
                <button class="btn btn-ghost" onclick="post('/api/mouse_click', {{btn:'right'}})">Right Click</button>
            </div>
            <button id="btn-lock" class="btn btn-ghost" style="margin-top:10px" onclick="toggleLock()">🔓 Unlock Mouse</button>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Media & Volume</span></div>
            <input type="text" id="ghost" placeholder="Type here to ghost type..." style="margin-bottom:10px">
            <button class="btn btn-primary" onclick="post('/api/ghost_type', {{text:document.getElementById('ghost').value}})">Inject Text</button>
            
            <div style="height:20px"></div>
            <input type="text" id="tts-input" placeholder="Text to speak..." style="margin-bottom:10px">
            <button class="btn btn-ghost" onclick="post('/api/speak', {{text:document.getElementById('tts-input').value}})">🔊 Speak Text</button>
            
            <div style="height:20px"></div>
            <div class="card-title" style="margin-bottom:10px">MEDIA CONTROLS</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
                <button class="btn btn-ghost" onclick="post('/api/media', {{action:'prev'}})">⏮</button>
                <button class="btn btn-primary" onclick="post('/api/media', {{action:'playpause'}})">⏯</button>
                <button class="btn btn-ghost" onclick="post('/api/media', {{action:'next'}})">⏭</button>
            </div>
            
            <div style="height:15px"></div>
            <div class="card-title" style="margin-bottom:10px">VOLUME</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
                <button class="btn btn-ghost" onclick="post('/api/volume', {{action:'down'}})">🔉 -</button>
                <button class="btn btn-danger" onclick="post('/api/volume', {{action:'mute'}})">🔇</button>
                <button class="btn btn-ghost" onclick="post('/api/volume', {{action:'up'}})">🔊 +</button>
            </div>
            
            <div style="height:20px"></div>
            <div class="card-title" style="margin-bottom:10px">HOTKEYS</div>
            <div class="grid-2">
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'alt_tab'}})">Alt+Tab</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'win_d'}})">Show Desktop</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'alt_f4'}})">Close Window</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'escape'}})">Escape</button>
            </div>
            
            <div style="height:15px"></div>
            <input type="text" id="url-input" placeholder="https://google.com" style="margin-bottom:5px">
            <button class="btn btn-ghost" onclick="openUrl()">🌐 Open Website</button>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Clipboard Sync</span></div>
            <div class="clip-box" id="pc-clip">Waiting...</div>
            <div class="grid-2">
                <button class="btn btn-ghost" onclick="getClip()">Pull</button>
                <button class="btn btn-primary" id="btn-copy-mobile" onclick="copyToClip()" style="display:none;">Copy to Device</button>
            </div>
            <div style="height:20px"></div>
            <input type="text" id="send-clip" placeholder="Text to push to PC">
            <button class="btn btn-primary" onclick="sendClip()">Push to PC</button>
        </div>
    </div>

    <!-- PRANK TAB -->
    <div id="prank" class="tab-content">
        <div class="card">
            <div class="card-header"><span class="card-title">Hacker Typer</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Active Status</span>
                <label class="switch"><input type="checkbox" id="chk-hacker" onchange="togglePrank('hacker', this)"><span class="slider"></span></label>
            </div>
            <select id="speed-hacker" class="speed-select"><option value="LAGGY">Laggy</option><option value="NORMAL">Normal</option><option value="FAST">Fast</option><option value="INSANE" selected>Insane</option></select>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Matrix Rain</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Active Status</span>
                <label class="switch"><input type="checkbox" id="chk-matrix" onchange="togglePrank('matrix', this)"><span class="slider"></span></label>
            </div>
            <select id="speed-matrix" class="speed-select"><option value="LAGGY">Laggy</option><option value="NORMAL">Normal</option><option value="FAST" selected>Fast</option><option value="INSANE">Insane</option></select>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Blue Screen</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Active Status</span>
                <label class="switch"><input type="checkbox" id="chk-bsod" onchange="togglePrank('bsod', this)"><span class="slider"></span></label>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Tools</span></div>
            <button class="btn btn-ghost" onclick="post('/api/prank', {{action:'jiggle'}})">✨ Mouse Jiggle</button>
            <div style="height:15px"></div>
            <textarea id="note" rows="3" placeholder="Message content..." style="width:100%;background:var(--surface-light);border:1px solid var(--border);color:white;border-radius:16px;padding:10px;font-family:sans-serif;margin-bottom:10px;"></textarea>
            <button class="btn btn-primary" onclick="post('/api/note_popup', {{text:document.getElementById('note').value}})">Deploy Popup</button>
        </div>
    </div>

    <!-- FILES TAB -->
    <div id="files" class="tab-content">
        <div class="card">
            <div class="card-header"><span class="card-title">Upload</span></div>
            <div style="border: 2px dashed var(--border); padding: 30px; text-align:center; border-radius:20px; cursor:pointer; margin-bottom:15px; color:var(--text-muted); transition:0.2s;" onclick="document.getElementById('file-inp').click()" onmouseover="this.style.borderColor='var(--primary)'" onmouseout="this.style.borderColor='var(--border)'">
                <div style="font-size:24px; margin-bottom:10px;">☁️</div>
                Tap to select file
            </div>
            <input type="file" id="file-inp" style="display:none" onchange="fileSelected()">
            <div id="upload-area" style="display:none; background: var(--surface-light); padding:15px; border-radius:16px; margin-bottom:10px;">
                <div style="font-size:13px; color:var(--text-muted); margin-bottom:10px;">Target: <span id="file-name" style="color:white; font-weight:bold;">...</span></div>
                <button class="btn btn-primary" onclick="uploadFile()">Upload File</button>
            </div>
            <div class="progress-container" id="progress-container"><div class="progress-bg"><div class="progress-fill" id="progress-fill"></div></div></div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-title">Local Files</span></div>
            <button class="btn btn-ghost" style="margin-bottom:15px" onclick="listFiles()">🔄 Refresh List</button>
            <div id="flist"></div>
        </div>
    </div>
</div>

    <!-- SETTINGS TAB -->
    <div id="settings" class="tab-content">
        <div class="card">
            <div class="card-header"><span class="card-title">System Info</span></div>
            <div id="sysinfo-container" style="font-family:monospace; font-size:13px;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:15px;">
                    <div style="background:rgba(139,92,246,0.1); padding:15px; border-radius:12px; text-align:center;">
                        <div style="font-size:20px; font-weight:bold; color:var(--primary);" id="sys-cpu-cores">-</div>
                        <div style="font-size:11px; color:var(--text-muted);">CPU CORES</div>
                    </div>
                    <div style="background:rgba(6,182,212,0.1); padding:15px; border-radius:12px; text-align:center;">
                        <div style="font-size:20px; font-weight:bold; color:var(--accent);" id="sys-ram">-</div>
                        <div style="font-size:11px; color:var(--text-muted);">RAM (GB)</div>
                    </div>
                    <div style="background:rgba(244,63,94,0.1); padding:15px; border-radius:12px; text-align:center;">
                        <div style="font-size:20px; font-weight:bold; color:var(--danger);" id="sys-disk">-</div>
                        <div style="font-size:11px; color:var(--text-muted);">DISK (GB)</div>
                    </div>
                    <div style="background:rgba(34,197,94,0.1); padding:15px; border-radius:12px; text-align:center;">
                        <div style="font-size:20px; font-weight:bold; color:#22c55e;" id="sys-uptime">-</div>
                        <div style="font-size:11px; color:var(--text-muted);">UPTIME</div>
                    </div>
                </div>
                <button class="btn btn-ghost" onclick="loadSysInfo()">🔄 Refresh</button>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header"><span class="card-title">Quick Actions</span></div>
            <div class="grid-2">
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'win_e'}})">📁 File Explorer</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'ctrl_shift_esc'}})">📊 Task Manager</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'print_screen'}})">📸 Print Screen</button>
                <button class="btn btn-ghost" onclick="post('/api/hotkey', {{action:'win_l'}})">🔐 Lock Screen</button>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header"><span class="card-title">About</span></div>
            <div style="text-align:center; padding:10px;">
                <div style="font-size:40px; margin-bottom:10px;">🖥️</div>
                <div style="font-size:18px; font-weight:bold; margin-bottom:5px;">PC Controller 2.0</div>
                <div style="font-size:13px; color:var(--text-muted);" id="app-version">v{APP_VERSION}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:10px;">Auto-updates every 5 minutes</div>
            </div>
            <button class="btn btn-primary" onclick="checkForUpdate()" style="margin-top:15px;">🔄 Check for Updates</button>
        </div>
    </div>
</div>

<nav class="bottom-nav">
    <button class="nav-item active" onclick="sw('dash', this, 'Dashboard')">📊 <span>Home</span></button>
    <button class="nav-item" onclick="sw('input', this, 'Input')">🖱️ <span>Input</span></button>
    <button class="nav-item" onclick="sw('prank', this, 'Pranks')">🎭 <span>Pranks</span></button>
    <button class="nav-item" onclick="sw('files', this, 'Files')">📂 <span>Files</span></button>
    <button class="nav-item" onclick="sw('settings', this, 'Settings'); loadSysInfo();">⚙️ <span>Settings</span></button>
</nav>

<script>
// --- LIVE STREAM LOGIC ---
var liveMode = false;

function toggleLive(checkbox) {{
    liveMode = checkbox.checked;
    var img = document.getElementById('ss-img');
    var badge = document.getElementById('live-badge');
    var overlay = document.getElementById('ss-overlay');
    var container = document.getElementById('screen-container');

    if (liveMode) {{
        img.src = '/api/live_stream';
        img.classList.add('live');
        img.classList.remove('loaded');
        badge.style.display = 'block';
        container.classList.add('live-mode');
    }} else {{
        img.src = '';
        img.classList.remove('live');
        badge.style.display = 'none';
        container.classList.remove('live-mode');
        overlay.style.opacity = '1';
        overlay.style.display = 'flex';
    }}
}}

// --- REST OF LOGIC ---
function doLogin() {{ 
    var pwd = document.getElementById('login-pwd').value; 
    
    // THE VARIABLE {UI_PASSWORD} IS INSERTED HERE FROM PYTHON
    if(pwd === '{UI_PASSWORD}') {{ 
        
        document.getElementById('login-overlay').style.opacity = '0';
        setTimeout(() => {{ document.getElementById('login-overlay').style.display = 'none'; document.getElementById('main-app').style.display = 'block'; }}, 300);
    }} else {{ 
        alert("ACCESS DENIED"); 
    }} 
}}
function sw(id, btn, title) {{ 
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active')); 
    document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active')); 
    document.getElementById(id).classList.add('active'); 
    btn.classList.add('active'); 
    document.getElementById('page-title').innerText = title; 
    if(id === 'files') listFiles(); 
}}
function post(url, data) {{ fetch(url, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(data)}}); }}
function shoot() {{ 
    if(liveMode) return; // Don't shoot if in live mode
    var txt = document.getElementById('ss-overlay'); 
    var img = document.getElementById('ss-img'); 
    txt.style.display = 'none'; 
    img.style.display = 'block'; 
    img.src = ''; 
    img.classList.remove('loaded'); 
    fetch('/api/screenshot').then(r=>r.json()).then(d=>{{ 
        if(d.img) {{ img.src = 'data:image/jpeg;base64,' + d.img; img.classList.add('loaded'); }} 
        else txt.style.display = 'flex'; 
    }}); 
}}
function setCircle(elementId, percentage) {{ 
    var el = document.getElementById(elementId); if(!el) return; 
    el.innerText = percentage + "%"; 
    var parent = el.parentElement; 
    var color = elementId === 'cpu-circle' ? '#8b5cf6' : '#06b6d4'; 
    parent.style.background = `conic-gradient(${{color}} ${{percentage}}%, rgba(255,255,255,0.05) 0%)`; 
}}
setInterval(function(){{ 
    fetch('/api/status').then(r=>r.json()).then(d=>{{ 
        document.getElementById('active-app').innerText = "ACTIVE: " + (d.app.length > 25 ? d.app.substring(0,25)+'...' : d.app); 
        setCircle('cpu-circle', d.cpu); setCircle('ram-circle', d.ram); 
        var lockBtn = document.getElementById('btn-lock'); 
        if(d.mouse_locked){{ lockBtn.innerText="🔒 Unlock Mouse"; lockBtn.classList.replace('btn-ghost','btn-danger'); }} 
        else {{ lockBtn.innerText="🔓 Lock Mouse"; lockBtn.classList.replace('btn-danger','btn-ghost'); }} 
    }}); 
}}, 2000);
function getClip() {{ 
    document.getElementById('pc-clip').innerText = 'Reading...'; 
    document.getElementById('btn-copy-mobile').style.display = 'none'; 
    fetch('/api/clipboard_get').then(r=>r.json()).then(d=>{{ 
        var txt = d.text || "Clipboard Empty"; 
        document.getElementById('pc-clip').innerText = txt; 
        var copyBtn = document.getElementById('btn-copy-mobile'); 
        if (d.text && d.text.length > 0) {{ copyBtn.style.display = 'block'; }} else {{ copyBtn.style.display = 'none'; }} 
    }}); 
}}
function copyToClip() {{ 
    var txt = document.getElementById('pc-clip').innerText; 
    if (navigator.clipboard && window.isSecureContext) {{ 
        navigator.clipboard.writeText(txt).then(() => {{ 
            var btn = document.getElementById('btn-copy-mobile'); 
            var originalText = btn.innerText; 
            btn.innerText = "COPIED!"; 
            setTimeout(() => {{ btn.innerText = originalText; }}, 1500); 
        }}); 
    }} else {{ alert("Manual copy required:\\n" + txt); }} 
}}
function sendClip() {{ post('/api/clipboard_send', {{text: document.getElementById('send-clip').value}}); }}
function fileSelected() {{ 
    var file = document.getElementById('file-inp').files[0]; 
    if(file) {{ 
        document.getElementById('upload-area').style.display = 'block'; 
        document.getElementById('file-name').innerText = file.name; 
        document.getElementById('progress-container').style.display = 'none'; 
    }} 
}}
function uploadFile() {{ 
    var inp = document.getElementById('file-inp'); 
    if(inp.files.length === 0) return; 
    var fd = new FormData(); fd.append('file', inp.files[0]); 
    var progressContainer = document.getElementById('progress-container'); 
    var progressBar = document.getElementById('progress-fill'); 
    progressContainer.style.display = 'block'; 
    progressBar.style.width = '0%'; 
    var xhr = new XMLHttpRequest(); 
    xhr.upload.addEventListener("progress", function(evt) {{ 
        if (evt.lengthComputable) {{ 
            var percentComplete = Math.round(evt.loaded / evt.total * 100); 
            progressBar.style.width = percentComplete + "%"; 
        }} 
    }}); 
    xhr.onload = function() {{ 
        if (this.status == 200) {{ 
            progressBar.style.width = "100%"; 
            setTimeout(function(){{ progressContainer.style.display = 'none'; document.getElementById('upload-area').style.display = 'none'; }}, 2000); 
        }} else {{ alert("Upload failed"); }} 
    }}; 
    xhr.onerror = function() {{ alert("Upload error"); }}; 
    xhr.open("POST", "/api/upload"); xhr.send(fd); 
}}
function listFiles() {{ 
    document.getElementById('flist').innerHTML = 'Scanning...'; 
    fetch('/api/files_list').then(r=>r.json()).then(list=>{{ 
        var html = ''; 
        if(list.length === 0) html = '<div style="text-align:center;color:var(--text-muted);padding:20px;">No files found</div>'; 
        list.forEach(f=> {{ 
            html+='<div class="file-item"><div class="file-info" style="display:flex;align-items:center"><span class="file-icon">📄</span><span class="file-name">'+f+'</span></div><a href="/api/files_download/'+encodeURIComponent(f)+'" class="download-btn">Save</a></div>'; 
        }}); 
        document.getElementById('flist').innerHTML = html; 
    }}); 
}}
function togglePrank(act, checkbox) {{ 
    var state = checkbox.checked ? 'on' : 'off'; 
    var speed = 'NORMAL'; 
    if (act === 'hacker') speed = document.getElementById('speed-hacker').value; 
    if (act === 'matrix') speed = document.getElementById('speed-matrix').value; 
    post('/api/prank', {{action: act, state: state, speed: speed}}); 
}}
function doAction(act) {{ 
    var p = prompt("Enter Admin Password"); 
    if(p) post('/api/action', {{action:act, password:p}}); 
}}
function runCmd() {{ 
    var p = prompt("Enter Admin Password"); 
    if(p) {{ 
        var cmd = document.getElementById('cmd-input').value; 
        document.getElementById('cmd-out').innerText = "Running..."; 
        fetch('/api/exec', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{cmd:cmd, password:p}})}}).then(r=>r.json()).then(d=>{{ document.getElementById('cmd-out').innerText = d.output || d.status; }}); 
    }} 
}}
function openUrl() {{ var url = document.getElementById('url-input').value; if(url) post('/api/open_url', {{url:url}}); }}
function toggleLock() {{ post('/api/media', {{action:'lock_mouse'}}); }}

// --- NEW: System Info ---
function loadSysInfo() {{
    fetch('/api/sysinfo').then(r=>r.json()).then(d=>{{
        if(d.error) return;
        document.getElementById('sys-cpu-cores').innerText = d.cpu_cores;
        document.getElementById('sys-ram').innerText = d.ram_used_gb + '/' + d.ram_total_gb;
        document.getElementById('sys-disk').innerText = d.disk_used_gb + '/' + d.disk_total_gb;
        document.getElementById('sys-uptime').innerText = d.uptime;
    }});
}}

// --- NEW: Check for Updates ---
function checkForUpdate() {{
    var btn = event.target;
    btn.innerText = 'Checking...';
    fetch('/api/check_update', {{method:'POST'}}).then(r=>r.json()).then(d=>{{
        if(d.updated) {{
            btn.innerText = '✅ Updated!';
            alert('Update downloaded! Please restart PC Controller.');
        }} else {{
            btn.innerText = '✅ Up to date!';
        }}
        setTimeout(()=>{{ btn.innerText = '🔄 Check for Updates'; }}, 3000);
    }}).catch(()=>{{
        btn.innerText = '❌ Error';
        setTimeout(()=>{{ btn.innerText = '🔄 Check for Updates'; }}, 3000);
    }});
}}

// --- NEW: Power Actions with Password ---
function doPower(act) {{
    var p = prompt("Enter Admin Password");
    if(p) post('/api/power', {{action:act, password:p}});
}}

var sx, sy; var pad = document.getElementById('pad'); 
pad.addEventListener('touchstart', function(e){{ sx = e.touches[0].clientX; sy = e.touches[0].clientY; }}); 
pad.addEventListener('touchmove', function(e){{ e.preventDefault(); var dx = (e.touches[0].clientX - sx) * 2.0; var dy = (e.touches[0].clientY - sy) * 2.0; post('/api/mouse_rel', {{x:dx, y:dy}}); sx = e.touches[0].clientX; sy = e.touches[0].clientY; }});
</script>
</body>
</html>
"""

if __name__ == '__main__':
    # Start tunnel thread
    t = threading.Thread(target=start_tunnel_thread)
    t.daemon = True
    t.start()
    
    # Start auto-update checker (checks every 5 minutes)
    if UPDATER_AVAILABLE:
        start_update_checker()
    
    print(f"[PC Controller] Starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)