import os
import time
import threading
import pyautogui
import pyperclip
import webbrowser
from flask import Blueprint, request, jsonify
from app import config
from app.security import require_auth

control_bp = Blueprint('control', __name__)

# State
mouse_locked = False

# Input blocker
try:
    from input_blocker import block_mouse, block_keyboard, get_status as get_block_status
    INPUT_BLOCKER_AVAILABLE = True
except ImportError:
    INPUT_BLOCKER_AVAILABLE = False
    def block_mouse(b=True): return False
    def block_keyboard(b=True): return False
    def get_block_status(): return {'mouse_blocked': False, 'keyboard_blocked': False}

@control_bp.route('/api/mouse_click', methods=['POST'])
@require_auth
def mouse_click():
    data = request.get_json(silent=True) or {}
    if not mouse_locked:
        pyautogui.click(button=data.get('btn', 'left'))
    return jsonify({'status': 'success'})

@control_bp.route('/api/mouse_rel', methods=['POST'])
@require_auth
def mouse_rel():
    data = request.get_json(silent=True) or {}
    if not mouse_locked:
        pyautogui.moveRel(int(data.get('x', 0)), int(data.get('y', 0)))
    return jsonify({'status': 'success'})

@control_bp.route('/api/ghost_type', methods=['POST'])
@require_auth
def ghost_type():
    data = request.get_json(silent=True) or {}
    pyautogui.write(data.get('text', ''), interval=0.05)
    return jsonify({'status': 'success'})

@control_bp.route('/api/speak', methods=['POST'])
@require_auth
def speak():
    data = request.get_json(silent=True) or {}
    text_to_speak = data.get('text', '')
    lang = data.get('lang', 'auto')
    
    def run_speech():
        temp_path = None
        try:
            from gtts import gTTS
            from playsound import playsound
            import tempfile
            
            if lang == 'auto':
                has_bangla = any('\u0980' <= c <= '\u09FF' for c in text_to_speak)
                detected_lang = 'bn' if has_bangla else 'en'
            else:
                detected_lang = lang
                
            tts = gTTS(text=text_to_speak, lang=detected_lang, slow=False)
            temp_path = os.path.join(tempfile.gettempdir(), f'tts_{time.time()}.mp3')
            tts.save(temp_path)
            playsound(temp_path)
        except Exception:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 150)
                engine.say(text_to_speak)
                engine.runAndWait()
            except Exception:
                pass
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    threading.Thread(target=run_speech).start()
    return jsonify({'status': 'speaking'})

@control_bp.route('/api/clipboard_get', methods=['GET'])
@require_auth
def clipboard_get():
    try:
        return jsonify({'text': pyperclip.paste()})
    except Exception:
        return jsonify({'text': ''})

@control_bp.route('/api/clipboard_send', methods=['POST'])
@require_auth
def clipboard_send():
    data = request.get_json(silent=True) or {}
    pyperclip.copy(data.get('text', ''))
    return jsonify({'status': 'copied'})

@control_bp.route('/api/media', methods=['POST'])
@require_auth
def media_control():
    global mouse_locked
    data = request.get_json(silent=True) or {}
    act = data.get('action')
    if act == 'playpause': pyautogui.press('playpause')
    elif act == 'next': pyautogui.press('nexttrack')
    elif act == 'prev': pyautogui.press('prevtrack')
    elif act == 'lock_mouse': mouse_locked = not mouse_locked
    return jsonify({'status': 'ok'})

@control_bp.route('/api/volume', methods=['POST'])
@require_auth
def volume_control():
    data = request.get_json(silent=True) or {}
    act = data.get('action')
    if act == 'up': pyautogui.press('volumeup')
    elif act == 'down': pyautogui.press('volumedown')
    elif act == 'mute': pyautogui.press('volumemute')
    return jsonify({'status': 'ok'})

@control_bp.route('/api/hotkey', methods=['POST'])
@require_auth
def keyboard_hotkey():
    data = request.get_json(silent=True) or {}
    act = data.get('action')
    if act == 'alt_tab': pyautogui.hotkey('alt', 'tab')
    elif act == 'win_d': pyautogui.hotkey('win', 'd')
    elif act == 'alt_f4': pyautogui.hotkey('alt', 'F4')
    elif act == 'win_l': pyautogui.hotkey('win', 'l')
    elif act == 'win_e': pyautogui.hotkey('win', 'e')
    elif act == 'ctrl_shift_esc': pyautogui.hotkey('ctrl', 'shift', 'esc')
    elif act == 'print_screen': pyautogui.press('printscreen')
    elif act == 'escape': pyautogui.press('escape')
    elif act == 'enter': pyautogui.press('enter')
    elif act == 'backspace': pyautogui.press('backspace')
    elif act == 'space': pyautogui.press('space')
    return jsonify({'status': 'ok'})

@control_bp.route('/api/open_url', methods=['POST'])
@require_auth
def open_url():
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    if url:
        webbrowser.open(url)
    return jsonify({'status': 'opened'})

@control_bp.route('/api/input_block', methods=['POST'])
@require_auth
def input_block():
    data = request.get_json(silent=True) or {}
    act = data.get('action')
    target = data.get('target', 'mouse')
    
    if target == 'mouse':
        result = block_mouse(act == 'on')
        return jsonify({'status': 'ok', 'mouse_blocked': result})
    elif target == 'keyboard':
        result = block_keyboard(act == 'on')
        return jsonify({'status': 'ok', 'keyboard_blocked': result})
    elif target == 'status':
        status = get_block_status()
        status['available'] = INPUT_BLOCKER_AVAILABLE
        return jsonify(status)
    return jsonify({'status': 'error', 'message': 'Unknown target'})

@control_bp.route('/api/brightness', methods=['POST'])
@require_auth
def brightness_control():
    try:
        import screen_brightness_control as sbc
        data = request.get_json(silent=True) or {}
        act = data.get('action')
        value = data.get('value', 50)
        
        if act == 'set': sbc.set_brightness(value)
        elif act == 'up': sbc.set_brightness(min(100, sbc.get_brightness()[0] + 10))
        elif act == 'down': sbc.set_brightness(max(0, sbc.get_brightness()[0] - 10))
        return jsonify({'status': 'ok', 'brightness': sbc.get_brightness()[0]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@control_bp.route('/api/sound', methods=['POST'])
@require_auth
def play_sound():
    try:
        import winsound
        data = request.get_json(silent=True) or {}
        sound_type = data.get('type', 'beep')
        if sound_type == 'beep':
            winsound.Beep(data.get('freq', 1000), data.get('duration', 500))
        elif sound_type == 'system':
            winsound.PlaySound(data.get('name', 'SystemAsterisk'), winsound.SND_ALIAS)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
