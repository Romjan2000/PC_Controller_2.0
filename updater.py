"""
PC Controller - Auto Update Module
Checks for updates every 5 minutes and applies them automatically.
"""

import os
import sys
import time
import threading
import requests
import zipfile
import shutil
from io import BytesIO

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_config():
    """Load configuration from .env file"""
    config = {
        'auto_update': True,
        'check_interval': 300,  # 5 minutes
        'github_repo': 'YOUR_USERNAME/PC_Controller',
        'telegram_bot_token': None,
        'telegram_chat_id': None
    }
    
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'AUTO_UPDATE':
                        config['auto_update'] = value.lower() == 'true'
                    elif key == 'UPDATE_CHECK_INTERVAL':
                        config['check_interval'] = int(value)
                    elif key == 'GITHUB_REPO':
                        config['github_repo'] = value
                    elif key == 'TELEGRAM_BOT_TOKEN':
                        config['telegram_bot_token'] = value
                    elif key == 'TELEGRAM_CHAT_ID':
                        config['telegram_chat_id'] = value
    
    return config

def get_local_version():
    """Get the current local version"""
    version_file = os.path.join(BASE_DIR, 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read().strip()
    return '0.0.0'

def get_remote_version(repo):
    """Get the latest version from GitHub"""
    try:
        url = f"https://raw.githubusercontent.com/{repo}/main/VERSION"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"[UPDATER] Error checking remote version: {e}")
    return None

def compare_versions(local, remote):
    """Compare version strings. Returns True if remote is newer."""
    try:
        local_parts = [int(x) for x in local.split('.')]
        remote_parts = [int(x) for x in remote.split('.')]
        
        for i in range(max(len(local_parts), len(remote_parts))):
            l = local_parts[i] if i < len(local_parts) else 0
            r = remote_parts[i] if i < len(remote_parts) else 0
            if r > l:
                return True
            elif l > r:
                return False
        return False
    except:
        return False

def send_telegram_notification(config, message):
    """Send update notification via Telegram"""
    token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    
    if token and chat_id and token != 'REPLACE_ME' and chat_id != 'REPLACE_ME':
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={'chat_id': chat_id, 'text': message}, timeout=10)
        except:
            pass

def download_and_apply_update(config):
    """Download the latest version and apply the update"""
    repo = config['github_repo']
    
    try:
        # Download the zip
        zip_url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
        print(f"[UPDATER] Downloading update from {zip_url}...")
        
        response = requests.get(zip_url, timeout=60)
        if response.status_code != 200:
            print(f"[UPDATER] Failed to download update: HTTP {response.status_code}")
            return False
        
        # Extract to temp directory
        temp_dir = os.path.join(BASE_DIR, '_update_temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            zf.extractall(temp_dir)
        
        # Find the extracted folder (GitHub adds repo name)
        extracted_folder = None
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                extracted_folder = item_path
                break
        
        if not extracted_folder:
            print("[UPDATER] Could not find extracted folder")
            return False
        
        # Files to preserve (don't overwrite)
        preserve_files = ['.env', 'cloudflared.exe', 'ngrok.exe', 'venv']
        
        # Copy new files
        for item in os.listdir(extracted_folder):
            if item in preserve_files:
                continue
            
            src = os.path.join(extracted_folder, item)
            dst = os.path.join(BASE_DIR, item)
            
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except Exception as e:
                print(f"[UPDATER] Error copying {item}: {e}")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        print("[UPDATER] Update applied successfully!")
        return True
        
    except Exception as e:
        print(f"[UPDATER] Error applying update: {e}")
        return False

def check_for_updates(config):
    """Check for updates and apply if available"""
    if not config['auto_update']:
        return False
    
    local_version = get_local_version()
    remote_version = get_remote_version(config['github_repo'])
    
    if remote_version is None:
        return False
    
    print(f"[UPDATER] Local: v{local_version}, Remote: v{remote_version}")
    
    if compare_versions(local_version, remote_version):
        print(f"[UPDATER] New version available: {remote_version}")
        send_telegram_notification(config, f"🔄 PC Controller update available!\n\nCurrent: v{local_version}\nNew: v{remote_version}\n\nDownloading update...")
        
        if download_and_apply_update(config):
            send_telegram_notification(config, f"✅ PC Controller updated to v{remote_version}!\n\nPlease restart the controller to apply changes.")
            return True
        else:
            send_telegram_notification(config, f"❌ Failed to update PC Controller.\n\nPlease update manually.")
    
    return False

def update_checker_loop():
    """Background loop that checks for updates periodically"""
    config = get_config()
    
    # Wait a bit before first check (let the server start)
    time.sleep(30)
    
    while True:
        try:
            config = get_config()  # Reload config each time
            
            if config['auto_update']:
                print("[UPDATER] Checking for updates...")
                check_for_updates(config)
            
        except Exception as e:
            print(f"[UPDATER] Error in update loop: {e}")
        
        # Wait for next check (default 5 minutes)
        time.sleep(config.get('check_interval', 300))

def start_update_checker():
    """Start the update checker in a background thread"""
    thread = threading.Thread(target=update_checker_loop, daemon=True)
    thread.start()
    print("[UPDATER] Auto-update checker started (checking every 5 minutes)")
    return thread

# For manual update check
def manual_check():
    """Manually trigger an update check"""
    config = get_config()
    return check_for_updates(config)

if __name__ == '__main__':
    # Test the updater
    print("Testing update checker...")
    config = get_config()
    print(f"Config: {config}")
    print(f"Local version: {get_local_version()}")
    print(f"Remote version: {get_remote_version(config['github_repo'])}")
