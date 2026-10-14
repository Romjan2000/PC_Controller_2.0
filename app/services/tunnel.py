import os
import re
import time
import subprocess
import requests
from app import config

def send_telegram_message(message):
    """Send alert message to Telegram bot if credentials are configured."""
    if config.TELEGRAM_BOT_TOKEN == "REPLACE_ME" or config.TELEGRAM_CHAT_ID == "REPLACE_ME":
        return
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": config.TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception:
        pass

def ensure_cloudflared():
    """Ensure cloudflared executable exists, auto-downloading it if missing."""
    local_path = os.path.join(config.BASE_DIR, 'cloudflared.exe')
    if os.path.exists(local_path):
        return local_path
        
    import shutil
    which_path = shutil.which('cloudflared')
    if which_path:
        return which_path

    print("[CLOUDFLARE] cloudflared.exe not found. Auto-downloading...")
    download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try:
        import urllib.request
        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(local_path, 'wb') as out_f:
                out_f.write(resp.read())
        print("[CLOUDFLARE] Downloaded cloudflared.exe successfully!")
        return local_path
    except Exception as e:
        print(f"[CLOUDFLARE] Auto-download failed: {e}")
        return None

def start_tunnel():
    """Start Cloudflare Tunnel (preferred) with automatic fallback to ngrok."""
    public_url = None
    
    # 1. Try Cloudflare Tunnel
    try:
        cloudflared_path = ensure_cloudflared()
        if not cloudflared_path:
            raise FileNotFoundError("Could not locate or download cloudflared")
            
        process = subprocess.Popen(
            [cloudflared_path, 'tunnel', '--url', f'http://localhost:{config.PORT}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        
        # Scan for the TryCloudflare generated URL (up to 30s)
        for _ in range(30):
            line = process.stdout.readline()
            if line:
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    public_url = match.group(1)
                    print(f"[CLOUDFLARE] Tunnel LIVE: {public_url}")
                    send_telegram_message(f"🚀 PC CONTROLLER STARTED\n🌐 Cloudflare Tunnel\nLink: {public_url}")
                    return public_url
            time.sleep(1)
    except FileNotFoundError:
        print("[INFO] Cloudflared not found, trying ngrok...")
    except Exception as e:
        print(f"[WARN] Cloudflare tunnel error: {e}, trying ngrok...")
        
    # 2. Try ngrok
    try:
        ngrok_path = os.path.join(config.BASE_DIR, 'ngrok.exe')
        if not os.path.exists(ngrok_path):
            ngrok_path = 'ngrok'
        subprocess.Popen([ngrok_path, 'http', str(config.PORT)], creationflags=0x08000000)
        time.sleep(3)
        for _ in range(10):
            try:
                public_url = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2).json()['tunnels'][0]['public_url']
                print(f"[NGROK] Tunnel LIVE: {public_url}")
                send_telegram_message(f"🚀 PC CONTROLLER STARTED\n📡 Ngrok Tunnel\nLink: {public_url}")
                return public_url
            except Exception:
                time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Ngrok tunnel error: {e}")
        
    # 3. Local only fallback
    print(f"[WARN] No tunnel available. Access locally at: http://localhost:{config.PORT}")
    send_telegram_message(f"⚠️ PC Controller started (LOCAL ONLY)\nNo tunnel available\nLocal: http://localhost:{config.PORT}")
    return f"http://localhost:{config.PORT}"
