# ============================================================
#  PC Controller 2.0 - One-Line Installer
#  Run this command in PowerShell:
#  irm https://raw.githubusercontent.com/Romjan2000/PC_Controller_2.0/main/install.ps1 | iex
# ============================================================

$ErrorActionPreference = "Stop"

# --- Configuration ---
$REPO_URL = "https://github.com/Romjan2000/PC_Controller_2.0"
$INSTALL_DIR = "$env:USERPROFILE\PC_Controller"
$CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

# --- Colors ---
function Write-Color($text, $color = "White") {
    Write-Host $text -ForegroundColor $color
}

function Write-Banner {
    Clear-Host
    Write-Color ""
    Write-Color "  ╔═══════════════════════════════════════════════════════════╗" "Cyan"
    Write-Color "  ║                                                           ║" "Cyan"
    Write-Color "  ║                  PC CONTROLLER INSTALLER                  ║" "Cyan"
    Write-Color "  ║                                                           ║" "Cyan"
    Write-Color "  ╚═══════════════════════════════════════════════════════════╝" "Cyan"
    Write-Color ""
}

function Write-Step($step, $text) {
    Write-Color "  [$step] $text" "Yellow"
}

function Write-Success($text) {
    Write-Color "  [✓] $text" "Green"
}

function Write-Error($text) {
    Write-Color "  [✗] $text" "Red"
}

function Write-Info($text) {
    Write-Color "  [i] $text" "Gray"
}

# --- Main Installation ---
Write-Banner

# Step 1: Check Python
Write-Step "1/7" "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 8) {
            Write-Success "Python $major.$minor found"
        }
        else {
            throw "Python 3.8+ required, found $major.$minor"
        }
    }
}
catch {
    Write-Error "Python 3.8+ is required but not found!"
    Write-Color ""
    Write-Color "  Please install Python from: https://python.org/downloads" "Cyan"
    Write-Color "  Make sure to check 'Add Python to PATH' during installation!" "Yellow"
    Write-Color ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Create/Check Install Directory
Write-Step "2/7" "Setting up installation directory..."
if (Test-Path $INSTALL_DIR) {
    Write-Info "Existing installation found at $INSTALL_DIR"
    $response = Read-Host "  Reinstall? (y/n)"
    if ($response -ne "y") {
        Write-Color "  Installation cancelled." "Yellow"
        exit 0
    }
    Remove-Item -Path $INSTALL_DIR -Recurse -Force
}
New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
Write-Success "Directory created: $INSTALL_DIR"

# Step 3: Download Repository
Write-Step "3/7" "Downloading PC Controller..."
$zipUrl = "$REPO_URL/archive/refs/heads/main.zip"
$zipPath = "$env:TEMP\PC_Controller.zip"
$extractPath = "$env:TEMP\PC_Controller_extract"

try {
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    
    # Extract
    if (Test-Path $extractPath) { Remove-Item $extractPath -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    
    # Move contents (GitHub zips have a folder inside)
    $innerFolder = Get-ChildItem $extractPath | Select-Object -First 1
    Get-ChildItem "$($innerFolder.FullName)\*" | Move-Item -Destination $INSTALL_DIR -Force
    
    # Cleanup
    Remove-Item $zipPath -Force
    Remove-Item $extractPath -Recurse -Force
    
    Write-Success "Downloaded successfully"
}
catch {
    Write-Error "Failed to download: $_"
    exit 1
}

# Step 4: Create Virtual Environment
Write-Step "4/7" "Creating Python virtual environment..."
Set-Location $INSTALL_DIR
python -m venv venv
Write-Success "Virtual environment created"

# Step 5: Install Dependencies
Write-Step "5/7" "Installing Python dependencies..."
& "$INSTALL_DIR\venv\Scripts\pip.exe" install -r requirements.txt --quiet
Write-Success "Dependencies installed"

# Step 6: Download Cloudflared
Write-Step "6/7" "Downloading Cloudflare Tunnel..."
try {
    Invoke-WebRequest -Uri $CLOUDFLARED_URL -OutFile "$INSTALL_DIR\cloudflared.exe" -UseBasicParsing
    Write-Success "Cloudflared downloaded"
}
catch {
    Write-Info "Could not download cloudflared (optional for remote access)"
}

# Step 7: Configuration Wizard
Write-Step "7/7" "Configuration Setup..."
Write-Color ""
Write-Color "  ┌─────────────────────────────────────────────────────────────┐" "Magenta"
Write-Color "  │              🔧  CONFIGURATION WIZARD  🔧                   │" "Magenta"
Write-Color "  └─────────────────────────────────────────────────────────────┘" "Magenta"
Write-Color ""

# UI Password
Write-Color "  Enter a password for the Web UI login:" "Cyan"
$uiPassword = Read-Host "  UI Password"
if ([string]::IsNullOrEmpty($uiPassword)) { $uiPassword = "admin123" }

# Admin Password
Write-Color ""
Write-Color "  Enter a password for Admin actions (shutdown/restart):" "Cyan"
$adminPassword = Read-Host "  Admin Password"
if ([string]::IsNullOrEmpty($adminPassword)) { $adminPassword = "admin123" }

# Hash the admin password
$adminHash = python -c "import hashlib; print(hashlib.sha256('$adminPassword'.encode()).hexdigest())"

# Telegram Setup
Write-Color ""
Write-Color "  ┌─────────────────────────────────────────────────────────────┐" "Blue"
Write-Color "  │              📱  TELEGRAM SETUP (Optional)                  │" "Blue"
Write-Color "  └─────────────────────────────────────────────────────────────┘" "Blue"
Write-Color ""
Write-Color "  To receive notifications when PC Controller starts:" "Gray"
Write-Color "  1. Open Telegram and search for @BotFather" "Gray"
Write-Color "  2. Send /newbot and follow the instructions" "Gray"
Write-Color "  3. Copy the API token you receive" "Gray"
Write-Color ""

$botToken = Read-Host "  Telegram Bot Token (or press Enter to skip)"
$chatId = ""

if (![string]::IsNullOrEmpty($botToken)) {
    Write-Color ""
    Write-Color "  To get your Chat ID:" "Gray"
    Write-Color "  1. Open Telegram and search for @userinfobot" "Gray"
    Write-Color "  2. Start the bot and it will show your ID" "Gray"
    Write-Color ""
    $chatId = Read-Host "  Telegram Chat ID"
}

if ([string]::IsNullOrEmpty($botToken)) { $botToken = "REPLACE_ME" }
if ([string]::IsNullOrEmpty($chatId)) { $chatId = "REPLACE_ME" }

# Create .env file
$envContent = @"
# ========================
# PC CONTROLLER CONFIG
# ========================

# --- SECURITY ---
APP_PASSWORD_PLAIN=$uiPassword
APP_PASSWORD_HASH=$adminHash

# --- TELEGRAM NOTIFICATIONS ---
TELEGRAM_BOT_TOKEN=$botToken
TELEGRAM_CHAT_ID=$chatId

# --- SERVER SETTINGS ---
PORT=1010
MAX_UPLOAD_SIZE_MB=1024

# --- AUTO UPDATE ---
AUTO_UPDATE=true
UPDATE_CHECK_INTERVAL=300
GITHUB_REPO=Romjan2000/PC_Controller_2.0
"@

$envContent | Out-File -FilePath "$INSTALL_DIR\.env" -Encoding UTF8
Write-Success "Configuration saved"

# Create Desktop Shortcut
Write-Color ""
$createShortcut = Read-Host "  Create desktop shortcut? (y/n)"
if ($createShortcut -eq "y") {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\PC Controller.lnk")
    $Shortcut.TargetPath = "$INSTALL_DIR\run.bat"
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.IconLocation = "shell32.dll,12"
    $Shortcut.Save()
    Write-Success "Desktop shortcut created"
}

# Add to Startup
$addStartup = Read-Host "  Start PC Controller on Windows startup? (y/n)"
if ($addStartup -eq "y") {
    $startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$startupPath\PC Controller.lnk")
    $Shortcut.TargetPath = "$INSTALL_DIR\run.bat"
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.WindowStyle = 7  # Minimized
    $Shortcut.Save()
    Write-Success "Added to Windows startup"
}

# --- Complete! ---
Write-Color ""
Write-Color "  ╔═══════════════════════════════════════════════════════════╗" "Green"
Write-Color "  ║                                                           ║" "Green"
Write-Color "  ║           ✅  INSTALLATION COMPLETE!  ✅                  ║" "Green"
Write-Color "  ║                                                           ║" "Green"
Write-Color "  ╚═══════════════════════════════════════════════════════════╝" "Green"
Write-Color ""
Write-Color "  Installation Location: $INSTALL_DIR" "Cyan"
Write-Color ""
Write-Color "  To start PC Controller:" "Yellow"
Write-Color "    1. Open the folder: $INSTALL_DIR" "Gray"
Write-Color "    2. Double-click 'run.bat'" "Gray"
Write-Color "    3. Check Telegram for the access link!" "Gray"
Write-Color ""

$startNow = Read-Host "  Start PC Controller now? (y/n)"
if ($startNow -eq "y") {
    Start-Process "$INSTALL_DIR\run.bat" -WorkingDirectory $INSTALL_DIR
    Write-Success "PC Controller is starting..."
    Write-Color "  Check your Telegram for the access URL!" "Cyan"
}

Write-Color ""
Write-Color "  Press Enter to close this window..." "Gray"
Read-Host

