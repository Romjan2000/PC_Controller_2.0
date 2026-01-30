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

# Input blocking (real mouse/keyboard lock)
try:
    from input_blocker import block_mouse, block_keyboard, get_status as get_block_status
    INPUT_BLOCKER_AVAILABLE = True
except ImportError:
    INPUT_BLOCKER_AVAILABLE = False
    def block_mouse(b=True): return False
    def block_keyboard(b=True): return False
    def get_block_status(): return {'mouse_blocked': False, 'keyboard_blocked': False}

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
matrix_display_proc = None  # Track Matrix display process

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
    lang = request.json.get('lang', 'auto')  # 'en', 'bn', or 'auto'
    
    def run_speech():
        temp_path = None
        try:
            # Try using gTTS (Google Text-to-Speech) for natural voice
            from gtts import gTTS
            from playsound import playsound
            import tempfile
            
            # Auto-detect language based on characters
            if lang == 'auto':
                # Check if text contains Bangla characters (Unicode range)
                has_bangla = any('\u0980' <= c <= '\u09FF' for c in text_to_speak)
                detected_lang = 'bn' if has_bangla else 'en'
            else:
                detected_lang = lang
            
            # Create speech
            tts = gTTS(text=text_to_speak, lang=detected_lang, slow=False)
            
            # Save to temp file
            temp_path = os.path.join(tempfile.gettempdir(), f'tts_{time.time()}.mp3')
            tts.save(temp_path)
            
            # Play using playsound
            playsound(temp_path)
            
        except ImportError:
            # Fallback to pyttsx3 if gTTS not available
            try:
                engine = pyttsx3.init()
                # Try to improve voice quality
                voices = engine.getProperty('voices')
                # Use a female voice if available (usually clearer)
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 150)  # Slightly slower for clarity
                engine.say(text_to_speak)
                engine.runAndWait()
            except: pass
        except Exception as e:
            print(f"[TTS Error] {e}")
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
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
    color = data.get('color', 'green')
    length = data.get('length', 'medium')
    
    # Map actions to script files
    script_map = {
        'hacker': 'hacker_prank.py', 
        'bsod': 'bsod_prank.py', 
        'matrix': 'matrix_rain.py',
        'crazy_mouse': 'crazy_mouse.py',
        'random_sounds': 'random_sounds.py'
    }
    
    # Toggle-based pranks (on/off)
    if action in script_map:
        if state == 'on' and action not in active_pranks:
            script_path = get_script_path(script_map[action])
            if os.path.exists(script_path):
                # Matrix rain gets extra arguments
                if action == 'matrix':
                    proc = subprocess.Popen([sys.executable, script_path, speed, color, length], creationflags=0x00000008, close_fds=True)
                else:
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
    
    # One-shot pranks
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
        subprocess.Popen([sys.executable, get_script_path('cd_tray.py'), 'eject'], creationflags=0x00000008)
        return jsonify({'status': 'ejected'})
    
    if action == 'cd_close':
        subprocess.Popen([sys.executable, get_script_path('cd_tray.py'), 'close'], creationflags=0x00000008)
        return jsonify({'status': 'closed'})
    
    if action == 'cd_disco':
        subprocess.Popen([sys.executable, get_script_path('cd_tray.py'), 'disco', '5'], creationflags=0x00000008)
        return jsonify({'status': 'disco'})
    
    if action == 'scary':
        subprocess.Popen([sys.executable, get_script_path('scary_popup.py')], creationflags=0x00000008)
        return jsonify({'status': 'scared'})
    
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

@app.route('/api/matrix_image', methods=['POST'])
def matrix_image():
    """Upload an image and display it as Matrix-style ASCII art"""
    global matrix_display_proc
    
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({'status': 'no file'})
    
    # Close any existing matrix display
    try:
        if matrix_display_proc and matrix_display_proc.poll() is None:
            matrix_display_proc.terminate()
    except:
        pass
    
    f = request.files['file']
    # Save to temp location
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), 'matrix_img_temp.png')
    f.save(temp_path)
    
    # Run the matrix image script and track the process
    matrix_display_proc = subprocess.Popen([sys.executable, get_script_path('matrix_image.py'), temp_path], creationflags=0x00000008)
    return jsonify({'status': 'displaying'})

@app.route('/api/matrix_close', methods=['POST'])
def matrix_close():
    """Close the Matrix display"""
    global matrix_display_proc
    try:
        if matrix_display_proc and matrix_display_proc.poll() is None:
            matrix_display_proc.terminate()
            matrix_display_proc = None
            return jsonify({'status': 'closed'})
    except:
        pass
    return jsonify({'status': 'not_running'})

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

@app.route('/api/check_update')
def check_update():
    """Check if a newer version is available and download if found"""
    try:
        from updater import get_local_version, get_remote_version, compare_versions, get_config, download_and_apply_update
        
        config = get_config()
        local_v = get_local_version()
        remote_v = get_remote_version(config['github_repo'])
        
        if remote_v is None:
            return jsonify({'status': 'error', 'message': 'Could not check remote version'})
        
        has_update = compare_versions(local_v, remote_v)
        
        if has_update:
            # Download the update files
            download_and_apply_update(config)
            
        return jsonify({
            'status': 'ok',
            'local_version': local_v,
            'remote_version': remote_v,
            'update_available': has_update
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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

# --- NEW: Task Manager ---
@app.route('/api/processes')
def list_processes():
    """List running processes with name, PID, and memory usage"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                info = proc.info
                mem_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'memory_mb': round(mem_mb, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Sort by memory usage (highest first)
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        return jsonify({'status': 'ok', 'processes': processes[:50]})  # Top 50
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/kill_process', methods=['POST'])
def kill_process():
    """Kill a process by PID"""
    try:
        pid = request.json.get('pid')
        if not pid:
            return jsonify({'status': 'error', 'message': 'No PID provided'})
        
        proc = psutil.Process(int(pid))
        proc.terminate()
        return jsonify({'status': 'ok', 'killed': pid})
    except psutil.NoSuchProcess:
        return jsonify({'status': 'error', 'message': 'Process not found'})
    except psutil.AccessDenied:
        return jsonify({'status': 'error', 'message': 'Access denied - run as admin'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Restart Controller ---
@app.route('/api/restart', methods=['POST'])
def restart_controller():
    """Restart the PC Controller to apply updates"""
    try:
        # Start a new instance before killing current one
        script_path = os.path.abspath(__file__)
        subprocess.Popen([sys.executable, script_path], creationflags=0x00000008)
        
        # Schedule shutdown of current instance
        def delayed_shutdown():
            time.sleep(1)
            os._exit(0)
        
        threading.Thread(target=delayed_shutdown).start()
        return jsonify({'status': 'restarting'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Scheduled Tasks ---
scheduled_tasks = {}  # {id: {'action': action, 'time': scheduled_time, 'timer': timer_obj}}
schedule_counter = 0

@app.route('/api/schedule', methods=['POST'])
def create_schedule():
    """Schedule shutdown/restart/sleep at a specific time"""
    global schedule_counter
    try:
        action = request.json.get('action')  # shutdown, restart, sleep
        delay_seconds = request.json.get('delay')  # seconds from now
        
        if action not in ['shutdown', 'restart', 'sleep']:
            return jsonify({'status': 'error', 'message': 'Invalid action'})
        
        def execute_scheduled():
            if action == 'shutdown':
                os.system('shutdown /s /t 0')
            elif action == 'restart':
                os.system('shutdown /r /t 0')
            elif action == 'sleep':
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            # Remove from active schedules
            if schedule_id in scheduled_tasks:
                del scheduled_tasks[schedule_id]
        
        schedule_counter += 1
        schedule_id = schedule_counter
        timer = threading.Timer(int(delay_seconds), execute_scheduled)
        timer.start()
        
        scheduled_tasks[schedule_id] = {
            'id': schedule_id,
            'action': action,
            'delay': delay_seconds,
            'created': time.time()
        }
        
        return jsonify({'status': 'ok', 'schedule_id': schedule_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/schedules')
def list_schedules():
    """List active scheduled tasks"""
    return jsonify({'status': 'ok', 'schedules': list(scheduled_tasks.values())})

@app.route('/api/cancel_schedule', methods=['POST'])
def cancel_schedule():
    """Cancel a scheduled task"""
    try:
        schedule_id = request.json.get('id')
        if schedule_id in scheduled_tasks:
            del scheduled_tasks[schedule_id]
            return jsonify({'status': 'ok', 'cancelled': schedule_id})
        return jsonify({'status': 'error', 'message': 'Schedule not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Window Manager ---
@app.route('/api/windows')
def list_windows():
    """List open windows"""
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        windows = []
        
        def enum_callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if title and len(title.strip()) > 0:
                        windows.append({'hwnd': hwnd, 'title': title})
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        return jsonify({'status': 'ok', 'windows': windows})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/focus_window', methods=['POST'])
def focus_window():
    """Bring window to front"""
    try:
        import ctypes
        hwnd = request.json.get('hwnd')
        ctypes.windll.user32.SetForegroundWindow(int(hwnd))
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/close_window', methods=['POST'])
def close_window():
    """Close a window"""
    try:
        import ctypes
        hwnd = request.json.get('hwnd')
        WM_CLOSE = 0x0010
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_CLOSE, 0, 0)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/minimize_window', methods=['POST'])
def minimize_window():
    """Minimize a window"""
    try:
        import ctypes
        hwnd = request.json.get('hwnd')
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(int(hwnd), SW_MINIMIZE)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: File Browser ---
@app.route('/api/browse')
def browse_files():
    """List files in a directory"""
    try:
        path = request.args.get('path', os.path.expanduser('~'))
        if not os.path.exists(path):
            return jsonify({'status': 'error', 'message': 'Path not found'})
        
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                is_dir = os.path.isdir(item_path)
                size = 0 if is_dir else os.path.getsize(item_path)
                items.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': is_dir,
                    'size': size
                })
            except:
                continue
        
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return jsonify({
            'status': 'ok',
            'path': path,
            'parent': os.path.dirname(path),
            'items': items[:100]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/open_file', methods=['POST'])
def open_file():
    """Open file with default application"""
    try:
        path = request.json.get('path')
        os.startfile(path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    """Delete a file or folder"""
    try:
        path = request.json.get('path')
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Live Screen Stream ---
@app.route('/api/screen_stream')
def screen_stream():
    """MJPEG stream of the screen"""
    fps = int(request.args.get('fps', 10))
    quality = int(request.args.get('quality', 30))
    
    def generate():
        while True:
            try:
                img = pyautogui.screenshot()
                img = img.resize((img.width // 2, img.height // 2))
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=quality)
                frame = buffer.getvalue()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
                time.sleep(1.0 / fps)
            except:
                break
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- NEW: App Launcher ---
APPS_CONFIG_FILE = os.path.join(BASE_DIR, 'apps.json')

def load_apps():
    """Load apps from config file"""
    if os.path.exists(APPS_CONFIG_FILE):
        with open(APPS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_apps(apps):
    """Save apps to config file"""
    with open(APPS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(apps, f, indent=2)

@app.route('/api/apps')
def list_apps():
    """List configured apps"""
    return jsonify({'status': 'ok', 'apps': load_apps()})

@app.route('/api/launch_app', methods=['POST'])
def launch_app():
    """Launch an app by path"""
    try:
        path = request.json.get('path')
        subprocess.Popen(path, shell=True)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/add_app', methods=['POST'])
def add_app():
    """Add a new app to launcher"""
    try:
        name = request.json.get('name')
        path = request.json.get('path')
        icon = request.json.get('icon', '')  # Base64 or emoji
        
        apps = load_apps()
        apps.append({'name': name, 'path': path, 'icon': icon})
        save_apps(apps)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/remove_app', methods=['POST'])
def remove_app():
    """Remove an app from launcher"""
    try:
        path = request.json.get('path')
        apps = load_apps()
        apps = [a for a in apps if a['path'] != path]
        save_apps(apps)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/extract_icon', methods=['POST'])
def extract_icon():
    """Extract icon from .exe file"""
    try:
        path = request.json.get('path')
        if not path.lower().endswith('.exe') or not os.path.exists(path):
            return jsonify({'status': 'error', 'message': 'Invalid exe path'})
        
        # Try to extract icon using PIL and win32api
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
                
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                icon_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                win32gui.DestroyIcon(large[0])
                if small:
                    win32gui.DestroyIcon(small[0])
                
                return jsonify({'status': 'ok', 'icon': f'data:image/png;base64,{icon_b64}'})
        except:
            pass
        
        return jsonify({'status': 'error', 'message': 'Could not extract icon'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Voice Commands ---
@app.route('/api/voice_command', methods=['POST'])
def voice_command():
    """Execute a voice command"""
    try:
        command = request.json.get('command', '').lower()
        
        # Common app names mapping
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
        
        # Volume commands
        if any(w in command for w in ['volume up', 'ভলিউম আপ', 'আওয়াজ বাড়াও']):
            pyautogui.press('volumeup')
            pyautogui.press('volumeup')
            pyautogui.press('volumeup')
            return jsonify({'status': 'ok', 'action': 'volume_up'})
        
        if any(w in command for w in ['volume down', 'ভলিউম ডাউন', 'আওয়াজ কমাও']):
            pyautogui.press('volumedown')
            pyautogui.press('volumedown')
            pyautogui.press('volumedown')
            return jsonify({'status': 'ok', 'action': 'volume_down'})
        
        if any(w in command for w in ['mute', 'মিউট']):
            pyautogui.press('volumemute')
            return jsonify({'status': 'ok', 'action': 'mute'})
        
        # Media commands
        if any(w in command for w in ['play', 'pause', 'প্লে', 'পজ']):
            pyautogui.press('playpause')
            return jsonify({'status': 'ok', 'action': 'playpause'})
        
        if any(w in command for w in ['next', 'skip', 'নেক্সট', 'স্কিপ']):
            pyautogui.press('nexttrack')
            return jsonify({'status': 'ok', 'action': 'next'})
        
        if any(w in command for w in ['previous', 'back', 'আগের']):
            pyautogui.press('prevtrack')
            return jsonify({'status': 'ok', 'action': 'previous'})
        
        # App opening commands
        for app_name, app_cmd in app_commands.items():
            if app_name in command:
                subprocess.Popen(app_cmd, shell=True)
                return jsonify({'status': 'ok', 'action': f'opened_{app_name}'})
        
        # Open with "open" prefix
        if command.startswith('open ') or command.startswith('ওপেন '):
            app_name = command.replace('open ', '').replace('ওপেন ', '').strip()
            subprocess.Popen(f'start {app_name}', shell=True)
            return jsonify({'status': 'ok', 'action': f'opened_{app_name}'})
        
        # Shutdown/restart commands
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

# --- NEW: Input Blocking (Real Mouse/Keyboard Lock) ---
@app.route('/api/input_block', methods=['POST'])
def input_block():
    act = request.json.get('action')
    target = request.json.get('target', 'mouse')
    
    if target == 'mouse':
        if act == 'on':
            result = block_mouse(True)
        else:
            result = block_mouse(False)
        return jsonify({'status': 'ok', 'mouse_blocked': result})
    
    elif target == 'keyboard':
        if act == 'on':
            result = block_keyboard(True)
        else:
            result = block_keyboard(False)
        return jsonify({'status': 'ok', 'keyboard_blocked': result})
    
    elif target == 'status':
        status = get_block_status()
        status['available'] = INPUT_BLOCKER_AVAILABLE
        return jsonify(status)
    
    return jsonify({'status': 'error', 'message': 'Unknown target'})

# --- NEW: Screen Brightness ---
@app.route('/api/brightness', methods=['POST'])
def brightness_control():
    try:
        import screen_brightness_control as sbc
        act = request.json.get('action')
        value = request.json.get('value', 50)
        
        if act == 'set':
            sbc.set_brightness(value)
        elif act == 'up':
            current = sbc.get_brightness()[0]
            sbc.set_brightness(min(100, current + 10))
        elif act == 'down':
            current = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, current - 10))
        elif act == 'get':
            return jsonify({'brightness': sbc.get_brightness()[0]})
        
        return jsonify({'status': 'ok', 'brightness': sbc.get_brightness()[0]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Webcam Capture ---
@app.route('/api/webcam')
def webcam_capture():
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Convert to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            return jsonify({'status': 'ok', 'image': f'data:image/jpeg;base64,{img_base64}'})
        return jsonify({'status': 'error', 'message': 'Failed to capture'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- NEW: Play Sound ---
@app.route('/api/sound', methods=['POST'])
def play_sound():
    try:
        import winsound
        sound_type = request.json.get('type', 'beep')
        
        if sound_type == 'beep':
            freq = request.json.get('freq', 1000)
            duration = request.json.get('duration', 500)
            winsound.Beep(freq, duration)
        elif sound_type == 'system':
            name = request.json.get('name', 'SystemAsterisk')
            winsound.PlaySound(name, winsound.SND_ALIAS)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

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
        <!-- Screen Effects -->
        <div class="card">
            <div class="card-header"><span class="card-title">🖥️ Screen Effects</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Hacker Typer</span>
                <label class="switch"><input type="checkbox" id="chk-hacker" onchange="togglePrank('hacker', this)"><span class="slider"></span></label>
            </div>
            <div class="toggle-row">
                <span class="toggle-label">Matrix Rain</span>
                <label class="switch"><input type="checkbox" id="chk-matrix" onchange="toggleMatrixRain(this)"><span class="slider"></span></label>
            </div>
            <div style="display:flex; gap:10px; margin-top:8px; margin-bottom:8px;">
                <select id="matrix-color" class="speed-select" style="flex:1;">
                    <option value="green" selected>Green</option>
                    <option value="blue">Blue</option>
                    <option value="red">Red</option>
                    <option value="purple">Purple</option>
                    <option value="cyan">Cyan</option>
                    <option value="yellow">Yellow</option>
                    <option value="pink">Pink</option>
                    <option value="rainbow">Rainbow</option>
                    <option value="multi">Multi-Color</option>
                </select>
                <select id="matrix-length" class="speed-select" style="flex:1;">
                    <option value="short">Short</option>
                    <option value="medium" selected>Medium</option>
                    <option value="long">Long</option>
                </select>
            </div>
            <div class="toggle-row">
                <span class="toggle-label">Blue Screen (BSOD)</span>
                <label class="switch"><input type="checkbox" id="chk-bsod" onchange="togglePrank('bsod', this)"><span class="slider"></span></label>
            </div>
            <select id="speed-screen" class="speed-select" style="margin-top:10px"><option value="LAGGY">Laggy</option><option value="NORMAL">Normal</option><option value="FAST" selected>Fast</option><option value="INSANE">Insane</option></select>
        </div>

        <!-- Mouse Pranks -->
        <div class="card">
            <div class="card-header"><span class="card-title">🖱️ Mouse Pranks</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Crazy Mouse</span>
                <label class="switch"><input type="checkbox" id="chk-crazy-mouse" onchange="togglePrank('crazy_mouse', this)"><span class="slider"></span></label>
            </div>
            <div class="toggle-row" style="border:none; padding-bottom:0;">
                <span class="toggle-label">Block Physical Mouse</span>
                <label class="switch"><input type="checkbox" id="chk-block-mouse" onchange="toggleInputBlock('mouse', this)"><span class="slider"></span></label>
            </div>
            <div style="height:15px"></div>
            <button class="btn btn-ghost" onclick="post('/api/prank', {{action:'jiggle'}})">✨ Mouse Jiggle (One-shot)</button>
        </div>

        <!-- Keyboard Lock -->
        <div class="card">
            <div class="card-header"><span class="card-title">⌨️ Input Lock</span></div>
            <div class="toggle-row" style="border:none;">
                <span class="toggle-label">Block Physical Keyboard</span>
                <label class="switch"><input type="checkbox" id="chk-block-keyboard" onchange="toggleInputBlock('keyboard', this)"><span class="slider"></span></label>
            </div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:10px;">⚠️ Safety: Ctrl+Alt+Del always works</div>
        </div>

        <!-- Audio Pranks -->
        <div class="card">
            <div class="card-header"><span class="card-title">🔊 Audio Pranks</span></div>
            <div class="toggle-row">
                <span class="toggle-label">Random Sounds</span>
                <label class="switch"><input type="checkbox" id="chk-random-sounds" onchange="togglePrank('random_sounds', this)"><span class="slider"></span></label>
            </div>
            <div class="grid-2" style="margin-top:15px;">
                <button class="btn btn-ghost" onclick="post('/api/sound', {{type:'beep', freq:1000, duration:500}})">🔔 Beep</button>
                <button class="btn btn-ghost" onclick="post('/api/sound', {{type:'system', name:'SystemExclamation'}})">⚠️ Alert</button>
            </div>
        </div>


        <!-- Scary Popup -->
        <div class="card">
            <div class="card-header"><span class="card-title">💀 Scary Pranks</span></div>
            <button class="btn btn-danger" onclick="post('/api/prank', {{action:'scary'}})">😱 Scary Popup</button>
            <div style="height:15px"></div>
            <textarea id="note" rows="2" placeholder="Custom popup message..." style="width:100%;background:var(--surface-light);border:1px solid var(--border);color:white;border-radius:16px;padding:10px;font-family:sans-serif;margin-bottom:10px;"></textarea>
            <button class="btn btn-ghost" onclick="post('/api/note_popup', {{text:document.getElementById('note').value}})">📝 Deploy Custom Popup</button>
        </div>
        
        <!-- Matrix Image -->
        <div class="card">
            <div class="card-header"><span class="card-title">🖼️ Matrix Image</span></div>
            
            <!-- Upload zone (shown when no image) -->
            <div id="matrix-upload-zone" onclick="document.getElementById('matrix-img-input').click()" style="border: 2px dashed var(--border); padding: 30px 15px; text-align:center; border-radius:16px; cursor:pointer; color:var(--text-muted); transition:all 0.3s; background: rgba(139,92,246,0.02);">
                <div style="font-size:36px; margin-bottom:10px;">🖼️</div>
                <div style="font-size:14px; font-weight:600; color:var(--text-main);">Tap to select image</div>
                <div style="font-size:11px; margin-top:5px;">Image will convert to Matrix ASCII art</div>
            </div>
            <input type="file" id="matrix-img-input" accept="image/*" style="display:none" onchange="handleMatrixUpload()">
            
            <!-- Controls (shown after upload) -->
            <div id="matrix-controls" style="display:none;">
                <div style="display:flex; align-items:center; gap:12px; background:rgba(139,92,246,0.1); padding:12px 16px; border-radius:12px; margin-bottom:12px;">
                    <span style="font-size:24px;">✅</span>
                    <div style="flex:1;">
                        <div id="matrix-filename" style="font-size:13px; color:var(--text-main); font-weight:600;">image.jpg</div>
                        <div style="font-size:11px; color:var(--text-muted);">Ready to display</div>
                    </div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show on PC</span>
                    <label class="switch"><input type="checkbox" id="chk-matrix-display" onchange="toggleMatrixDisplay(this)"><span class="slider"></span></label>
                </div>
                <button class="btn btn-ghost" style="margin-top:12px; width:100%;" onclick="replaceMatrixImage()">🔄 Replace Image</button>
            </div>
        </div>
    </div>

    <!-- FILES TAB -->
    <div id="files" class="tab-content">
        <!-- Upload Section -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">☁️ Upload to PC</span>
            </div>
            <div id="drop-zone" style="border: 2px dashed var(--border); padding: 40px 20px; text-align:center; border-radius:20px; cursor:pointer; margin-bottom:15px; color:var(--text-muted); transition:all 0.3s; background: rgba(139,92,246,0.02);" onclick="document.getElementById('file-inp').click()">
                <div style="font-size:48px; margin-bottom:15px; opacity:0.8;">📁</div>
                <div style="font-size:16px; font-weight:600; color:var(--text-main); margin-bottom:5px;">Tap to select file</div>
                <div style="font-size:12px;">or drag and drop</div>
            </div>
            <input type="file" id="file-inp" style="display:none" onchange="fileSelected()">
            
            <!-- Selected file info -->
            <div id="upload-area" style="display:none; background: linear-gradient(135deg, rgba(139,92,246,0.1) 0%, rgba(6,182,212,0.1) 100%); padding:20px; border-radius:16px; margin-bottom:10px; border:1px solid var(--border);">
                <div style="display:flex; align-items:center; gap:15px; margin-bottom:15px;">
                    <div style="font-size:32px;">📄</div>
                    <div style="flex:1;">
                        <div id="file-name" style="color:white; font-weight:bold; font-size:14px; word-break:break-all;">...</div>
                        <div id="file-size" style="color:var(--text-muted); font-size:12px;"></div>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="uploadFile()" style="width:100%;">🚀 Upload Now</button>
            </div>
            
            <!-- Progress bar -->
            <div class="progress-container" id="progress-container" style="display:none; background:var(--surface-light); padding:20px; border-radius:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span id="upload-status" style="font-size:14px; color:var(--text-main); font-weight:600;">Uploading...</span>
                    <span id="progress-percent" style="font-size:14px; color:var(--primary); font-weight:bold;">0%</span>
                </div>
                <div class="progress-bg" style="margin-bottom:12px;"><div class="progress-fill" id="progress-fill"></div></div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; text-align:center;">
                    <div style="background:rgba(139,92,246,0.1); padding:10px; border-radius:8px;">
                        <div id="upload-speed" style="font-size:16px; font-weight:bold; color:var(--primary);">0 KB/s</div>
                        <div style="font-size:10px; color:var(--text-muted);">SPEED</div>
                    </div>
                    <div style="background:rgba(6,182,212,0.1); padding:10px; border-radius:8px;">
                        <div id="upload-transferred" style="font-size:16px; font-weight:bold; color:var(--accent);">0 MB</div>
                        <div style="font-size:10px; color:var(--text-muted);">UPLOADED</div>
                    </div>
                    <div style="background:rgba(34,197,94,0.1); padding:10px; border-radius:8px;">
                        <div id="upload-eta" style="font-size:16px; font-weight:bold; color:#22c55e;">--:--</div>
                        <div style="font-size:10px; color:var(--text-muted);">ETA</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Downloads Folder -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📥 PC Downloads Folder</span>
                <button class="btn btn-ghost" style="padding:8px 12px; font-size:12px;" onclick="listFiles()">🔄 Refresh</button>
            </div>
            <div id="flist" style="max-height:400px; overflow-y:auto;">
                <div style="text-align:center; padding:30px; color:var(--text-muted);">
                    <div style="font-size:32px; margin-bottom:10px;">📂</div>
                    <div>Tap Refresh to load files</div>
                </div>
            </div>
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
        
        <!-- Updates -->
        <div class="card">
            <div class="card-header"><span class="card-title">🔄 Updates</span></div>
            <div style="display:flex; align-items:center; gap:12px; background:rgba(139,92,246,0.1); padding:12px 16px; border-radius:12px; margin-bottom:12px;">
                <span style="font-size:24px;">📦</span>
                <div style="flex:1;">
                    <div style="font-size:13px; color:var(--text-main); font-weight:600;">Current Version</div>
                    <div id="current-version" style="font-size:18px; color:var(--primary); font-weight:bold;">{APP_VERSION}</div>
                </div>
            </div>
            <div id="update-status" style="display:none; background:rgba(34,197,94,0.1); padding:12px 16px; border-radius:12px; margin-bottom:12px; border:1px solid rgba(34,197,94,0.3);">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">✨</span>
                    <div style="flex:1;">
                        <div style="font-size:13px; color:#22c55e; font-weight:600;">New Version Available!</div>
                        <div id="new-version" style="font-size:16px; color:white; font-weight:bold;"></div>
                    </div>
                </div>
            </div>
            <div id="update-checking" style="display:none; text-align:center; padding:10px; color:var(--text-muted);">
                <span style="display:inline-block; animation: spin 1s linear infinite;">⏳</span> Checking for updates...
            </div>
            <div id="update-uptodate" style="display:none; text-align:center; padding:10px; color:#22c55e;">
                ✅ You're up to date!
            </div>
            <button class="btn btn-ghost" id="btn-check-update" onclick="checkForUpdates()" style="width:100%; margin-bottom:8px;">🔍 Check for Updates</button>
            <button class="btn btn-primary" id="btn-restart" onclick="restartController()" style="width:100%; display:none;">🔄 Restart with New Version</button>
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
    
    <!-- APPS TAB (NEW v2.4.0) -->
    <div id="apps" class="tab-content">
        
        <!-- Voice Command -->
        <div class="card">
            <div class="card-header"><span class="card-title">🎤 Voice Command</span></div>
            <div style="text-align:center; padding:15px;">
                <select id="voice-lang" style="width:100%; margin-bottom:15px;">
                    <option value="en-US">🇺🇸 English</option>
                    <option value="bn-BD">🇧🇩 বাংলা (Bangla)</option>
                </select>
                <button class="btn btn-primary" id="voice-btn" onclick="startVoice()" style="padding:25px; font-size:24px;">🎤</button>
                <div id="voice-status" style="margin-top:15px; color:var(--text-muted); font-size:13px;">Tap mic and speak</div>
                <div id="voice-result" style="margin-top:10px; color:var(--primary); font-weight:600;"></div>
            </div>
        </div>
        
        <!-- App Launcher -->
        <div class="card">
            <div class="card-header"><span class="card-title">🚀 App Launcher</span></div>
            <div id="app-grid" style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:15px;"></div>
            <div style="border-top:1px solid var(--border); padding-top:15px; margin-top:10px;">
                <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">Add New App</div>
                <input type="text" id="app-name" placeholder="App Name" style="margin-bottom:8px;">
                <input type="text" id="app-path" placeholder="Path (e.g. C:\\Program Files\\...\\app.exe)">
                <button class="btn btn-ghost" onclick="addNewApp()">➕ Add App</button>
            </div>
        </div>
        
        <!-- Window Manager -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">🪟 Window Manager</span>
                <button class="btn btn-ghost" onclick="loadWindows()" style="padding:8px 12px; font-size:12px;">🔄</button>
            </div>
            <div id="window-list" style="max-height:300px; overflow-y:auto;"></div>
        </div>
        
        <!-- Task Manager -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">🔧 Task Manager</span>
                <button class="btn btn-ghost" onclick="loadProcesses()" style="padding:8px 12px; font-size:12px;">🔄</button>
            </div>
            <div id="process-list" style="max-height:300px; overflow-y:auto;"></div>
        </div>
        
        <!-- Scheduled Tasks -->
        <div class="card">
            <div class="card-header"><span class="card-title">⏰ Schedule Action</span></div>
            <select id="sched-action" style="margin-bottom:10px;">
                <option value="shutdown">🔴 Shutdown</option>
                <option value="restart">🔄 Restart</option>
                <option value="sleep">💤 Sleep</option>
            </select>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:15px;">
                <button class="btn btn-ghost" onclick="scheduleIn(300)">5 min</button>
                <button class="btn btn-ghost" onclick="scheduleIn(1800)">30 min</button>
                <button class="btn btn-ghost" onclick="scheduleIn(3600)">1 hour</button>
            </div>
            <div id="active-schedules" style="font-size:12px; color:var(--text-muted);"></div>
        </div>
        
        <!-- File Browser -->
        <div class="card">
            <div class="card-header"><span class="card-title">📁 File Browser</span></div>
            <div style="display:flex; gap:8px; margin-bottom:12px;">
                <button class="btn btn-ghost" onclick="browseParent()" style="padding:10px;">⬆️ Up</button>
                <button class="btn btn-ghost" onclick="browseHome()" style="padding:10px; flex:1;">🏠 Home</button>
            </div>
            <div id="browse-path" style="font-size:11px; color:var(--text-muted); margin-bottom:10px; word-break:break-all;"></div>
            <div id="browse-list" style="max-height:300px; overflow-y:auto;"></div>
        </div>
        
        <!-- Live Screen Mirror -->
        <div class="card">
            <div class="card-header"><span class="card-title">📺 Live Screen Mirror</span></div>
            <select id="stream-fps" style="margin-bottom:10px;">
                <option value="10">10 FPS (Low - Fast)</option>
                <option value="15">15 FPS (Medium)</option>
                <option value="30">30 FPS (High - Smooth)</option>
            </select>
            <button class="btn btn-primary" id="stream-btn" onclick="toggleScreenMirror()">▶️ Start Mirror</button>
            <div id="mirror-container" style="display:none; margin-top:15px;">
                <img id="mirror-img" style="width:100%; border-radius:12px; border:1px solid var(--border);">
                <button class="btn btn-ghost" onclick="fullscreenMirror()" style="margin-top:10px;">🔲 Fullscreen</button>
            </div>
        </div>
        
    </div>
</div>

<nav class="bottom-nav">
    <button class="nav-item active" onclick="sw('dash', this, 'Dashboard')">📊 <span>Home</span></button>
    <button class="nav-item" onclick="sw('input', this, 'Input')">🖱️ <span>Input</span></button>
    <button class="nav-item" onclick="sw('prank', this, 'Pranks')">🎭 <span>Pranks</span></button>
    <button class="nav-item" onclick="sw('files', this, 'Files')">📂 <span>Files</span></button>
    <button class="nav-item" onclick="sw('apps', this, 'Apps'); loadAppData();">🚀 <span>Apps</span></button>
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
        // Show file size
        var sizeEl = document.getElementById('file-size');
        if(sizeEl) {{
            var size = file.size;
            var sizeStr = size < 1024 ? size + ' B' : 
                          size < 1048576 ? (size/1024).toFixed(1) + ' KB' : 
                          (size/1048576).toFixed(1) + ' MB';
            sizeEl.innerText = sizeStr;
        }}
        document.getElementById('progress-container').style.display = 'none'; 
    }} 
}}

function uploadFile() {{ 
    var inp = document.getElementById('file-inp'); 
    if(inp.files.length === 0) return;
    
    var file = inp.files[0];
    var fd = new FormData(); 
    fd.append('file', file);
    
    var progressContainer = document.getElementById('progress-container'); 
    var progressBar = document.getElementById('progress-fill');
    var progressPercent = document.getElementById('progress-percent');
    var uploadStatus = document.getElementById('upload-status');
    var uploadSpeed = document.getElementById('upload-speed');
    var uploadTransferred = document.getElementById('upload-transferred');
    var uploadEta = document.getElementById('upload-eta');
    
    progressContainer.style.display = 'block'; 
    progressBar.style.width = '0%';
    if(uploadStatus) uploadStatus.innerText = 'Starting upload...';
    
    var startTime = Date.now();
    var lastLoaded = 0;
    var lastTime = startTime;
    
    var xhr = new XMLHttpRequest(); 
    xhr.upload.addEventListener("progress", function(evt) {{ 
        if (evt.lengthComputable) {{ 
            var now = Date.now();
            var loaded = evt.loaded;
            var total = evt.total;
            var percentComplete = Math.round(loaded / total * 100);
            
            // Update progress bar
            progressBar.style.width = percentComplete + "%";
            if(progressPercent) progressPercent.innerText = percentComplete + "%";
            
            // Calculate speed (bytes per second)
            var timeDiff = (now - lastTime) / 1000;
            if(timeDiff > 0.5) {{  // Update every 0.5 seconds
                var bytesDiff = loaded - lastLoaded;
                var speed = bytesDiff / timeDiff;  // bytes per second
                
                // Format speed
                var speedStr;
                if(speed < 1024) speedStr = Math.round(speed) + ' B/s';
                else if(speed < 1048576) speedStr = (speed/1024).toFixed(1) + ' KB/s';
                else speedStr = (speed/1048576).toFixed(1) + ' MB/s';
                
                if(uploadSpeed) uploadSpeed.innerText = speedStr;
                
                // Calculate ETA
                var remaining = total - loaded;
                var eta = speed > 0 ? remaining / speed : 0;
                var etaStr;
                if(eta < 60) etaStr = Math.round(eta) + 's';
                else if(eta < 3600) etaStr = Math.floor(eta/60) + 'm ' + Math.round(eta%60) + 's';
                else etaStr = Math.floor(eta/3600) + 'h ' + Math.round((eta%3600)/60) + 'm';
                
                if(uploadEta) uploadEta.innerText = etaStr;
                
                lastLoaded = loaded;
                lastTime = now;
            }}
            
            // Format transferred bytes
            var transferredStr;
            if(loaded < 1024) transferredStr = loaded + ' B';
            else if(loaded < 1048576) transferredStr = (loaded/1024).toFixed(1) + ' KB';
            else if(loaded < 1073741824) transferredStr = (loaded/1048576).toFixed(1) + ' MB';
            else transferredStr = (loaded/1073741824).toFixed(2) + ' GB';
            
            var totalStr;
            if(total < 1024) totalStr = total + ' B';
            else if(total < 1048576) totalStr = (total/1024).toFixed(1) + ' KB';
            else if(total < 1073741824) totalStr = (total/1048576).toFixed(1) + ' MB';
            else totalStr = (total/1073741824).toFixed(2) + ' GB';
            
            if(uploadTransferred) uploadTransferred.innerText = transferredStr;
            if(uploadStatus) uploadStatus.innerText = 'Uploading... ' + transferredStr + ' / ' + totalStr;
        }} 
    }}); 
    
    xhr.onload = function() {{ 
        if (this.status == 200) {{ 
            progressBar.style.width = "100%";
            if(progressPercent) progressPercent.innerText = "100%";
            if(uploadStatus) uploadStatus.innerText = "✅ Upload Complete!";
            if(uploadSpeed) uploadSpeed.innerText = "Done";
            if(uploadEta) uploadEta.innerText = "0s";
            
            setTimeout(function(){{ 
                progressContainer.style.display = 'none'; 
                document.getElementById('upload-area').style.display = 'none';
                document.getElementById('file-inp').value = '';
            }}, 3000); 
        }} else {{ 
            if(uploadStatus) uploadStatus.innerText = "❌ Upload Failed";
            alert("Upload failed"); 
        }} 
    }}; 
    xhr.onerror = function() {{ 
        if(uploadStatus) uploadStatus.innerText = "❌ Upload Error";
        alert("Upload error"); 
    }}; 
    xhr.open("POST", "/api/upload"); 
    xhr.send(fd); 
}}

function listFiles() {{ 
    document.getElementById('flist').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);"><div style="font-size:24px;animation:pulse 1s infinite;">⏳</div>Loading files...</div>'; 
    fetch('/api/files_list').then(r=>r.json()).then(list=>{{ 
        var html = ''; 
        if(list.length === 0) {{
            html = '<div style="text-align:center;color:var(--text-muted);padding:30px;"><div style="font-size:32px;margin-bottom:10px;">📭</div>No files in Downloads folder</div>'; 
        }} else {{
            list.forEach(f=> {{ 
                // Choose icon based on extension
                var ext = f.split('.').pop().toLowerCase();
                var icon = '📄';
                if(['jpg','jpeg','png','gif','webp','bmp'].includes(ext)) icon = '🖼️';
                else if(['mp4','mkv','avi','mov','webm'].includes(ext)) icon = '🎬';
                else if(['mp3','wav','flac','ogg','m4a'].includes(ext)) icon = '🎵';
                else if(['zip','rar','7z','tar','gz'].includes(ext)) icon = '📦';
                else if(['pdf'].includes(ext)) icon = '📕';
                else if(['doc','docx'].includes(ext)) icon = '📝';
                else if(['xls','xlsx'].includes(ext)) icon = '📊';
                else if(['exe','msi'].includes(ext)) icon = '⚙️';
                else if(['txt','log'].includes(ext)) icon = '📃';
                else if(['py','js','html','css','json'].includes(ext)) icon = '💻';
                
                html+='<div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.03);padding:12px 16px;border-radius:12px;margin-bottom:8px;border:1px solid var(--border);transition:all 0.2s;" onmouseover="this.style.borderColor=\\'var(--primary)\\'" onmouseout="this.style.borderColor=\\'var(--border)\\'">';
                html+='<div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0;">';
                html+='<span style="font-size:24px;">'+icon+'</span>';
                html+='<span style="font-size:13px;color:var(--text-main);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+f+'</span>';
                html+='</div>';
                html+='<a href="/api/files_download/'+encodeURIComponent(f)+'" style="background:var(--primary);color:white;padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;">⬇️ Save</a>';
                html+='</div>'; 
            }});
        }}
        document.getElementById('flist').innerHTML = html; 
    }}).catch(e=>{{
        document.getElementById('flist').innerHTML = '<div style="text-align:center;color:var(--danger);padding:20px;">Error loading files</div>';
    }});
}}
function togglePrank(act, checkbox) {{ 
    var state = checkbox.checked ? 'on' : 'off'; 
    var speed = document.getElementById('speed-screen') ? document.getElementById('speed-screen').value : 'NORMAL'; 
    post('/api/prank', {{action: act, state: state, speed: speed}}); 
}}

// Matrix Rain with color and length options
function toggleMatrixRain(checkbox) {{
    var state = checkbox.checked ? 'on' : 'off';
    var speed = document.getElementById('speed-screen').value || 'NORMAL';
    var color = document.getElementById('matrix-color').value || 'green';
    var length = document.getElementById('matrix-length').value || 'medium';
    post('/api/prank', {{action: 'matrix', state: state, speed: speed, color: color, length: length}});
}}

// Toggle input blocking (real mouse/keyboard lock)
function toggleInputBlock(target, checkbox) {{
    var act = checkbox.checked ? 'on' : 'off';
    post('/api/input_block', {{action: act, target: target}});
}}

// Matrix Image - stored file data
var matrixImageFile = null;

// Handle Matrix image upload
function handleMatrixUpload() {{
    var inp = document.getElementById('matrix-img-input');
    if(inp.files.length === 0) return;
    
    matrixImageFile = inp.files[0];
    
    // Show controls, hide upload zone
    document.getElementById('matrix-upload-zone').style.display = 'none';
    document.getElementById('matrix-controls').style.display = 'block';
    document.getElementById('matrix-filename').innerText = matrixImageFile.name;
    document.getElementById('chk-matrix-display').checked = false;
}}

// Toggle Matrix display on/off
function toggleMatrixDisplay(checkbox) {{
    if(!matrixImageFile) {{
        checkbox.checked = false;
        return;
    }}
    
    if(checkbox.checked) {{
        // Upload and display
        var fd = new FormData();
        fd.append('file', matrixImageFile);
        fetch('/api/matrix_image', {{method:'POST', body: fd}})
            .then(r => r.json())
            .then(data => {{
                if(data.status !== 'displaying') {{
                    checkbox.checked = false;
                }}
            }});
    }} else {{
        // Close the display
        post('/api/matrix_close', {{}});
    }}
}}

// Replace Matrix image - go back to upload zone
function replaceMatrixImage() {{
    matrixImageFile = null;
    document.getElementById('matrix-upload-zone').style.display = 'block';
    document.getElementById('matrix-controls').style.display = 'none';
    document.getElementById('chk-matrix-display').checked = false;
    document.getElementById('matrix-img-input').value = '';
}}

// Check for updates
function checkForUpdates() {{
    document.getElementById('btn-check-update').disabled = true;
    document.getElementById('update-checking').style.display = 'block';
    document.getElementById('update-status').style.display = 'none';
    document.getElementById('update-uptodate').style.display = 'none';
    document.getElementById('btn-restart').style.display = 'none';
    
    fetch('/api/check_update')
        .then(r => r.json())
        .then(data => {{
            document.getElementById('update-checking').style.display = 'none';
            document.getElementById('btn-check-update').disabled = false;
            
            if(data.status === 'error') {{
                alert('Error checking for updates: ' + data.message);
                return;
            }}
            
            if(data.update_available) {{
                document.getElementById('new-version').innerText = 'v' + data.remote_version;
                document.getElementById('update-status').style.display = 'block';
                document.getElementById('btn-restart').style.display = 'block';
            }} else {{
                document.getElementById('update-uptodate').style.display = 'block';
            }}
        }})
        .catch(e => {{
            document.getElementById('update-checking').style.display = 'none';
            document.getElementById('btn-check-update').disabled = false;
            alert('Failed to check for updates');
        }});
}}

// Restart Controller with new version
function restartController() {{
    if(!confirm('Restart PC Controller now?')) return;
    
    document.getElementById('btn-restart').disabled = true;
    document.getElementById('btn-restart').innerText = '⏳ Restarting...';
    
    fetch('/api/restart', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{}})}})
        .then(r => r.json())
        .then(data => {{
            if(data.status === 'restarting') {{
                document.getElementById('btn-restart').innerText = '✅ Restarted! Refresh page...';
                setTimeout(() => {{ location.reload(); }}, 3000);
            }}
        }})
        .catch(e => {{
            document.getElementById('btn-restart').disabled = false;
            document.getElementById('btn-restart').innerText = '🔄 Restart with New Version';
        }});
}}

// ============ V2.4.0 NEW FEATURES ============

// --- Load App Data (called when Apps tab opens) ---
function loadAppData() {{
    loadApps();
    loadWindows();
    loadProcesses();
    browseHome();
}}

// --- App Launcher ---
function loadApps() {{
    fetch('/api/apps').then(r=>r.json()).then(data => {{
        var html = '';
        if(data.apps && data.apps.length > 0) {{
            data.apps.forEach(app => {{
                var icon = app.icon || '📦';
                if(app.icon && app.icon.startsWith('data:')) {{
                    icon = '<img src="'+app.icon+'" style="width:32px;height:32px;border-radius:6px;">';
                }}
                html += '<div onclick="launchApp(\\''+app.path.replace(/\\\\/g,'\\\\\\\\')+'\\')\" style="text-align:center;padding:12px;background:rgba(255,255,255,0.03);border-radius:12px;cursor:pointer;border:1px solid var(--border);">';
                html += '<div style="font-size:28px;">'+icon+'</div>';
                html += '<div style="font-size:11px;color:var(--text-muted);margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+app.name+'</div>';
                html += '</div>';
            }});
        }} else {{
            html = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:20px;">No apps added yet</div>';
        }}
        document.getElementById('app-grid').innerHTML = html;
    }});
}}

function launchApp(path) {{
    post('/api/launch_app', {{path: path}});
}}

function addNewApp() {{
    var name = document.getElementById('app-name').value;
    var path = document.getElementById('app-path').value;
    if(!name || !path) {{ alert('Enter app name and path'); return; }}
    
    fetch('/api/add_app', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name:name, path:path}})}})
        .then(r=>r.json())
        .then(data => {{
            document.getElementById('app-name').value = '';
            document.getElementById('app-path').value = '';
            loadApps();
        }});
}}

// --- Window Manager ---
function loadWindows() {{
    document.getElementById('window-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/windows').then(r=>r.json()).then(data => {{
        var html = '';
        if(data.windows && data.windows.length > 0) {{
            data.windows.forEach(w => {{
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:6px;border:1px solid var(--border);">';
                html += '<div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;">'+w.title+'</div>';
                html += '<div style="display:flex;gap:5px;">';
                html += '<button onclick="focusWin('+w.hwnd+')" style="padding:5px 10px;background:var(--primary);color:white;border:none;border-radius:6px;font-size:10px;cursor:pointer;">Switch</button>';
                html += '<button onclick="closeWin('+w.hwnd+')" style="padding:5px 10px;background:var(--danger);color:white;border:none;border-radius:6px;font-size:10px;cursor:pointer;">✕</button>';
                html += '</div></div>';
            }});
        }} else {{
            html = '<div style="text-align:center;color:var(--text-muted);padding:20px;">No windows found</div>';
        }}
        document.getElementById('window-list').innerHTML = html;
    }});
}}

function focusWin(hwnd) {{ post('/api/focus_window', {{hwnd: hwnd}}); }}
function closeWin(hwnd) {{ post('/api/close_window', {{hwnd: hwnd}}); loadWindows(); }}

// --- Task Manager ---
function loadProcesses() {{
    document.getElementById('process-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/processes').then(r=>r.json()).then(data => {{
        var html = '';
        if(data.processes && data.processes.length > 0) {{
            data.processes.forEach(p => {{
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:rgba(255,255,255,0.02);border-radius:6px;margin-bottom:4px;font-size:11px;">';
                html += '<div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+p.name+'</div>';
                html += '<div style="color:var(--text-muted);margin:0 10px;">'+p.memory_mb+' MB</div>';
                html += '<button onclick="killProc('+p.pid+')" style="padding:4px 8px;background:var(--danger);color:white;border:none;border-radius:4px;font-size:10px;cursor:pointer;">Kill</button>';
                html += '</div>';
            }});
        }}
        document.getElementById('process-list').innerHTML = html;
    }});
}}

function killProc(pid) {{
    if(!confirm('Kill this process?')) return;
    fetch('/api/kill_process', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{pid:pid}})}})
        .then(r=>r.json()).then(data => {{ loadProcesses(); }});
}}

// --- Voice Commands ---
var recognition = null;
function startVoice() {{
    if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
        alert('Voice not supported in this browser');
        return;
    }}
    
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = document.getElementById('voice-lang').value;
    recognition.continuous = false;
    
    document.getElementById('voice-status').innerText = '🔴 Listening...';
    document.getElementById('voice-btn').style.background = 'var(--danger)';
    
    recognition.onresult = function(event) {{
        var cmd = event.results[0][0].transcript;
        document.getElementById('voice-result').innerText = '"' + cmd + '"';
        document.getElementById('voice-status').innerText = 'Processing...';
        
        fetch('/api/voice_command', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{command:cmd}})}})
            .then(r=>r.json()).then(data => {{
                if(data.status === 'ok') {{
                    document.getElementById('voice-status').innerText = '✅ ' + (data.action || 'Done');
                }} else if(data.status === 'confirm') {{
                    if(confirm(data.message)) {{
                        post('/api/action', {{action: data.action, password: prompt('Admin password:')}});
                    }}
                    document.getElementById('voice-status').innerText = 'Tap mic and speak';
                }} else {{
                    document.getElementById('voice-status').innerText = '❓ Command not recognized';
                }}
            }});
    }};
    
    recognition.onerror = function(event) {{
        document.getElementById('voice-status').innerText = '❌ Error: ' + event.error;
        document.getElementById('voice-btn').style.background = '';
    }};
    
    recognition.onend = function() {{
        document.getElementById('voice-btn').style.background = '';
    }};
    
    recognition.start();
}}

// --- Scheduled Tasks ---
function scheduleIn(seconds) {{
    var action = document.getElementById('sched-action').value;
    fetch('/api/schedule', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{action:action, delay:seconds}})}})
        .then(r=>r.json()).then(data => {{
            if(data.status === 'ok') {{
                document.getElementById('active-schedules').innerText = '⏰ '+action+' scheduled in ' + Math.floor(seconds/60) + ' minutes';
            }}
        }});
}}

// --- File Browser ---
var currentBrowsePath = '';
function browseHome() {{ browseTo(''); }}
function browseParent() {{ 
    if(currentBrowsePath) {{
        var parent = currentBrowsePath.split(/[\\\\/]/).slice(0,-1).join('\\\\');
        browseTo(parent || '');
    }}
}}

function browseTo(path) {{
    currentBrowsePath = path;
    document.getElementById('browse-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/browse?path=' + encodeURIComponent(path)).then(r=>r.json()).then(data => {{
        if(data.status === 'error') {{
            document.getElementById('browse-list').innerHTML = '<div style="color:var(--danger);padding:20px;">'+data.message+'</div>';
            return;
        }}
        document.getElementById('browse-path').innerText = data.path;
        currentBrowsePath = data.path;
        
        var html = '';
        data.items.forEach(item => {{
            var icon = item.is_dir ? '📁' : '📄';
            html += '<div onclick="'+(item.is_dir ? "browseTo('"+item.path.replace(/\\\\/g,'\\\\\\\\')+"')" : "openBrowseFile('"+item.path.replace(/\\\\/g,'\\\\\\\\')+"')")+'" style="display:flex;align-items:center;gap:10px;padding:10px;background:rgba(255,255,255,0.02);border-radius:8px;margin-bottom:4px;cursor:pointer;border:1px solid var(--border);">';
            html += '<span style="font-size:20px;">'+icon+'</span>';
            html += '<span style="flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+item.name+'</span>';
            if(!item.is_dir) html += '<span style="font-size:10px;color:var(--text-muted);">'+(item.size/1024).toFixed(1)+' KB</span>';
            html += '</div>';
        }});
        document.getElementById('browse-list').innerHTML = html || '<div style="text-align:center;color:var(--text-muted);padding:20px;">Empty folder</div>';
    }});
}}

function openBrowseFile(path) {{
    post('/api/open_file', {{path: path}});
}}

// --- Live Screen Mirror ---
var mirrorActive = false;
function toggleScreenMirror() {{
    mirrorActive = !mirrorActive;
    var btn = document.getElementById('stream-btn');
    var container = document.getElementById('mirror-container');
    var img = document.getElementById('mirror-img');
    
    if(mirrorActive) {{
        var fps = document.getElementById('stream-fps').value;
        img.src = '/api/screen_stream?fps=' + fps + '&quality=40';
        container.style.display = 'block';
        btn.innerText = '⏹️ Stop Mirror';
        btn.style.background = 'var(--danger)';
    }} else {{
        img.src = '';
        container.style.display = 'none';
        btn.innerText = '▶️ Start Mirror';
        btn.style.background = '';
    }}
}}

function fullscreenMirror() {{
    var img = document.getElementById('mirror-img');
    if(img.requestFullscreen) img.requestFullscreen();
    else if(img.webkitRequestFullscreen) img.webkitRequestFullscreen();
}}

// ============ END V2.4.0 ============

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