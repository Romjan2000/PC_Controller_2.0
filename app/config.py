import os
import secrets
from dotenv import load_dotenv

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Server configuration
PORT = int(os.getenv('PORT', 1010))

# Passwords
UI_PASSWORD = os.getenv('APP_PASSWORD_PLAIN', '1122')
APP_PASSWORD_HASH = os.getenv('APP_PASSWORD_HASH', 'd05ad294422e1e6f4b6a1e7f9b8f0e7e9a1d5e1e3d2b8c6a1e5e9d4f3b2a1c0')

# Flask session secret key (use environment variable or generate random secret)
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))

# Telegram notifications
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'REPLACE_ME')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', 'REPLACE_ME')

# File uploads
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE_MB', 1024)) * 1024 * 1024

try:
    user_profile = os.environ.get('USERPROFILE', os.path.expanduser('~'))
    DOWNLOADS_FOLDER = os.path.join(user_profile, 'Downloads')
except Exception:
    DOWNLOADS_FOLDER = os.path.expanduser('~/Downloads')

UPLOAD_FOLDER = DOWNLOADS_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Version loader
def get_local_version():
    version_file = os.path.join(BASE_DIR, 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return '2.4.0'

APP_VERSION = get_local_version()

# Script path resolver
def get_script_path(script_name):
    return os.path.join(BASE_DIR, 'scripts', script_name)
