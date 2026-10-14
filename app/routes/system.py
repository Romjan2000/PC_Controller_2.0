import os
import sys
import time
import subprocess
import threading
import psutil
import win32gui
from flask import Blueprint, request, jsonify
from app import config
from app.security import require_auth, verify_password

system_bp = Blueprint('system', __name__)

# State
mouse_locked = False
scheduled_tasks = {}
schedule_counter = 0

try:
    from updater import get_local_version, get_remote_version, compare_versions, get_config, download_and_apply_update
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False

@system_bp.route('/api/status')
@require_auth
def get_status():
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        try:
            hwnd = win32gui.GetForegroundWindow()
            app_name = win32gui.GetWindowText(hwnd)
        except Exception:
            app_name = "Unknown"
        return jsonify({'app': app_name, 'cpu': cpu, 'ram': ram, 'mouse_locked': mouse_locked})
    except Exception:
        return jsonify({'app': 'Error', 'cpu': 0, 'ram': 0, 'mouse_locked': False})

@system_bp.route('/api/sysinfo')
@require_auth
def system_info():
    try:
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot_time = time.time() - psutil.boot_time()
        
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
            'version': config.APP_VERSION
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@system_bp.route('/api/action', methods=['POST'])
@require_auth
def system_action():
    data = request.get_json(silent=True) or {}
    if verify_password(data.get('password')):
        act = data.get('action')
        if act == 'shutdown':
            os.system("shutdown /s /t 0")
        elif act == 'restart':
            os.system("shutdown /r /t 0")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'wrong password'}), 403

@system_bp.route('/api/power', methods=['POST'])
@require_auth
def power_control():
    data = request.get_json(silent=True) or {}
    act = data.get('action')
    # Lock workstation does not require admin password
    if act == 'lock':
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return jsonify({'status': 'success'})
        
    if verify_password(data.get('password', '')):
        if act == 'sleep':
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif act == 'logoff':
            os.system("shutdown /l")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'wrong password'}), 403

@system_bp.route('/api/exec', methods=['POST'])
@require_auth
def exec_command():
    data = request.get_json(silent=True) or {}
    if verify_password(data.get('password')):
        try:
            cmd = data.get('cmd')
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            return jsonify({'status': 'success', 'output': out.decode('cp437', errors='ignore')})
        except Exception as e:
            return jsonify({'status': 'error', 'output': str(e)})
    return jsonify({'status': 'unauthorized'}), 403

@system_bp.route('/api/processes')
@require_auth
def list_processes():
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
        processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        return jsonify({'status': 'ok', 'processes': processes[:50]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/kill_process', methods=['POST'])
@require_auth
def kill_process():
    try:
        data = request.get_json(silent=True) or {}
        pid = data.get('pid')
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

@system_bp.route('/api/windows')
@require_auth
def list_windows():
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

@system_bp.route('/api/focus_window', methods=['POST'])
@require_auth
def focus_window():
    try:
        import ctypes
        hwnd = request.get_json(silent=True).get('hwnd')
        ctypes.windll.user32.SetForegroundWindow(int(hwnd))
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/close_window', methods=['POST'])
@require_auth
def close_window():
    try:
        import ctypes
        hwnd = request.get_json(silent=True).get('hwnd')
        WM_CLOSE = 0x0010
        ctypes.windll.user32.PostMessageW(int(hwnd), WM_CLOSE, 0, 0)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/minimize_window', methods=['POST'])
@require_auth
def minimize_window():
    try:
        import ctypes
        hwnd = request.get_json(silent=True).get('hwnd')
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(int(hwnd), SW_MINIMIZE)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/schedule', methods=['POST'])
@require_auth
def create_schedule():
    global schedule_counter
    try:
        data = request.get_json(silent=True) or {}
        action = data.get('action')
        delay_seconds = data.get('delay')
        if action not in ['shutdown', 'restart', 'sleep']:
            return jsonify({'status': 'error', 'message': 'Invalid action'})
        
        def execute_scheduled(sched_id):
            if action == 'shutdown':
                os.system('shutdown /s /t 0')
            elif action == 'restart':
                os.system('shutdown /r /t 0')
            elif action == 'sleep':
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            if sched_id in scheduled_tasks:
                del scheduled_tasks[sched_id]

        schedule_counter += 1
        schedule_id = schedule_counter
        timer = threading.Timer(int(delay_seconds), execute_scheduled, args=[schedule_id])
        timer.start()
        scheduled_tasks[schedule_id] = {
            'id': schedule_id,
            'action': action,
            'delay': delay_seconds,
            'created': time.time(),
            'timer': timer
        }
        return jsonify({'status': 'ok', 'schedule_id': schedule_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/schedules')
@require_auth
def list_schedules():
    out = []
    for s in scheduled_tasks.values():
        out.append({'id': s['id'], 'action': s['action'], 'delay': s['delay'], 'created': s['created']})
    return jsonify({'status': 'ok', 'schedules': out})

@system_bp.route('/api/cancel_schedule', methods=['POST'])
@require_auth
def cancel_schedule():
    try:
        schedule_id = request.get_json(silent=True).get('id')
        if schedule_id in scheduled_tasks:
            scheduled_tasks[schedule_id]['timer'].cancel()
            del scheduled_tasks[schedule_id]
            return jsonify({'status': 'ok', 'cancelled': schedule_id})
        return jsonify({'status': 'error', 'message': 'Schedule not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/version')
def get_version():
    return jsonify({'version': config.APP_VERSION, 'updater_available': UPDATER_AVAILABLE})

@system_bp.route('/api/check_update', methods=['GET', 'POST'])
@require_auth
def check_update():
    try:
        if not UPDATER_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'Updater not available'})
        cfg = get_config()
        local_v = get_local_version()
        remote_v = get_remote_version(cfg['github_repo'])
        if remote_v is None:
            return jsonify({'status': 'error', 'message': 'Could not check remote version'})
        has_update = compare_versions(local_v, remote_v)
        if has_update:
            download_and_apply_update(cfg)
        return jsonify({
            'status': 'ok',
            'local_version': local_v,
            'remote_version': remote_v,
            'update_available': has_update,
            'updated': has_update
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@system_bp.route('/api/restart', methods=['POST'])
@require_auth
def restart_controller():
    try:
        script_path = os.path.join(config.BASE_DIR, 'Controller.pyw')
        subprocess.Popen([sys.executable, script_path], creationflags=0x00000008)
        def delayed_shutdown():
            time.sleep(1)
            os._exit(0)
        threading.Thread(target=delayed_shutdown).start()
        return jsonify({'status': 'restarting'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
