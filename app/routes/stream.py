import io
import time
import base64
import pyautogui
from PIL import ImageGrab
from flask import Blueprint, request, jsonify, Response
from app.security import require_auth

stream_bp = Blueprint('stream', __name__)

@stream_bp.route('/api/screenshot')
@require_auth
def screenshot():
    try:
        ss = pyautogui.screenshot()
        img_byte_arr = io.BytesIO()
        ss.save(img_byte_arr, format='JPEG', quality=85)
        return jsonify({'img': base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')})
    except Exception:
        return jsonify({'img': None})

@stream_bp.route('/api/live_stream')
@require_auth
def live_stream():
    def generate():
        try:
            while True:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=40)
                frame = buf.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.05)
        except GeneratorExit:
            pass
        except Exception:
            pass
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@stream_bp.route('/api/screen_stream')
@require_auth
def screen_stream():
    fps = int(request.args.get('fps', 10))
    quality = int(request.args.get('quality', 30))
    
    def generate():
        while True:
            try:
                img = pyautogui.screenshot()
                img = img.resize((img.width // 2, img.height // 2))
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality)
                frame = buffer.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1.0 / fps)
            except Exception:
                break
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@stream_bp.route('/api/webcam')
@require_auth
def webcam_capture():
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            return jsonify({'status': 'ok', 'image': f'data:image/jpeg;base64,{img_base64}'})
        return jsonify({'status': 'error', 'message': 'Failed to capture'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
