# 🖥️ PC Controller 2.0

Control your Windows PC remotely from any device! Access your computer from your phone, tablet, or another computer via a sleek web interface.

![PC Controller](https://img.shields.io/badge/Platform-Windows-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## ⚡ One-Line Install (Recommended)

Open **PowerShell** and run this single command:

```powershell
irm https://raw.githubusercontent.com/Romjan2000/PC_Controller_2.0/main/install.ps1 | iex
```

This will automatically:
- ✅ Download PC Controller
- ✅ Set up Python virtual environment
- ✅ Install all dependencies
- ✅ Download Cloudflare Tunnel
- ✅ Guide you through configuration
- ✅ Create desktop shortcut (optional)
- ✅ Add to Windows startup (optional)

**The only manual step**: Create a Telegram bot for notifications (optional but recommended).

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📷 **Live Screen** | Real-time screen streaming with MJPEG |
| 🖱️ **Remote Mouse** | Touch trackpad for mouse control |
| ⌨️ **Ghost Typing** | Type text remotely on the target PC |
| 🔊 **Text-to-Speech** | Make your PC speak any text |
| 📁 **File Transfer** | Upload/download files to Downloads folder |
| 📋 **Clipboard Sync** | Share clipboard between devices |
| 🎭 **Pranks** | Hacker typer, Matrix rain, BSOD, and more |
| 📊 **System Stats** | Live CPU and RAM monitoring |
| ⚡ **System Control** | Shutdown, restart, run commands |
| 🔄 **Auto-Update** | Automatically updates every 5 minutes |

---

## 📱 Telegram Bot Setup

To receive the access URL on your phone:

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the API token you receive
4. Search for **@userinfobot** to get your Chat ID
5. Enter these when prompted during installation

---

## 🚀 Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

### 1. Download & Extract
```bash
git clone https://github.com/YOUR_USERNAME/PC_Controller.git
cd PC_Controller
```

### 2. Run Setup
Double-click `setup.bat` or run:
```bash
setup.bat
```
This will:
- Create a virtual environment
- Install Python dependencies
- Create `.env` config file

### 3. Download Cloudflare Tunnel (Recommended)
For remote access outside your network:
1. Download [cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest)
2. Rename to `cloudflared.exe`
3. Place in the PC_Controller folder

### 4. Start Controller
Double-click `run.bat` to start!

</details>

---

## ⚙️ Configuration

Edit `.env` file to customize:

```env
# UI Login Password
APP_PASSWORD_PLAIN=your_password

# Admin Actions Password (hashed)
APP_PASSWORD_HASH=your_hash

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Server Port
PORT=1010

# Auto-Update Settings
AUTO_UPDATE=true
UPDATE_CHECK_INTERVAL=300
```

### Generate Password Hash
```python
python -c "import hashlib; print(hashlib.sha256('YOUR_PASSWORD'.encode()).hexdigest())"
```

---

## 🔄 Auto-Update System

PC Controller automatically checks for updates every 5 minutes!

- Updates are downloaded from this GitHub repository
- Your `.env` configuration is preserved during updates
- You'll receive a Telegram notification when updates are applied
- Disable with `AUTO_UPDATE=false` in `.env`

---

## 📱 Usage

1. Open the tunnel URL on any device
2. Enter your password to login
3. Navigate using the bottom menu:
   - **Home** - Stats, screenshot, system controls
   - **Input** - Mouse, keyboard, clipboard
   - **Pranks** - Fun effects and popups
   - **Files** - Upload/download files

---

## 🔒 Security Notes

- Change the default password immediately
- The tunnel URL is public - keep it private
- Admin actions (shutdown/restart) require separate password
- Telegram notifications help track access

---

## 🛠️ Requirements

- Windows 10/11
- Python 3.8+
- Internet connection (for remote access)

---

## 📌 Troubleshooting

| Issue | Solution |
|-------|----------|
| `cloudflared not found` | Download cloudflared.exe to the folder |
| `Python not found` | Install Python 3.8+ and add to PATH |
| `Port already in use` | Change PORT in .env file |
| `Tunnel not working` | Check firewall settings |

---

## 📄 License

MIT License - Feel free to use and modify!

---

Made with ❤️ for remote PC control
