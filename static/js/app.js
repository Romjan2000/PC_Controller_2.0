// --- LIVE STREAM LOGIC ---
var liveMode = false;

function toggleLive(checkbox) {
    liveMode = checkbox.checked;
    var img = document.getElementById('ss-img');
    var badge = document.getElementById('live-badge');
    var overlay = document.getElementById('ss-overlay');
    var container = document.getElementById('screen-container');

    if (liveMode) {
        img.src = '/api/live_stream';
        img.classList.add('live');
        img.classList.remove('loaded');
        badge.style.display = 'block';
        container.classList.add('live-mode');
    } else {
        img.src = '';
        img.classList.remove('live');
        badge.style.display = 'none';
        container.classList.remove('live-mode');
        overlay.style.opacity = '1';
        overlay.style.display = 'flex';
    }
}

// --- WEBSOCKET & AUTHENTICATION ---
var socket = null;

function initWebSocket() {
    if (typeof io !== 'undefined' && !socket) {
        socket = io();
        socket.on('connect', function() {
            console.log('[WebSocket] Connected for low-latency input!');
        });
        socket.on('disconnect', function() {
            console.log('[WebSocket] Disconnected');
        });
    }
}

async function doLogin() { 
    var pwdInput = document.getElementById('login-pwd');
    var pwd = pwdInput ? pwdInput.value : '';
    if (!pwd) return;

    try {
        var res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({password: pwd})
        });
        var data = await res.json();
        
        if (res.ok && data.status === 'ok') {
            document.getElementById('login-overlay').style.opacity = '0';
            setTimeout(() => {
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('main-app').style.display = 'block';
            }, 300);
            initWebSocket();
        } else {
            alert(data.message || "ACCESS DENIED");
        }
    } catch (err) {
        alert("Connection error: " + err.message);
    }
}

// ==================== THEME MANAGEMENT ====================
function initTheme() {
    var savedStyle = localStorage.getItem('pc_controller_style') || 'glass';
    var savedMode = localStorage.getItem('pc_controller_mode') || 'dark';
    applyTheme(savedStyle, savedMode);
}

function applyTheme(style, mode) {
    document.documentElement.setAttribute('data-theme-style', style);
    document.documentElement.setAttribute('data-theme-mode', mode);
    localStorage.setItem('pc_controller_style', style);
    localStorage.setItem('pc_controller_mode', mode);

    document.querySelectorAll('.theme-card-option').forEach(el => el.classList.remove('active'));
    var activeCard = document.getElementById('theme-opt-' + style);
    if (activeCard) activeCard.classList.add('active');

    var btnDark = document.getElementById('mode-btn-dark');
    var btnLight = document.getElementById('mode-btn-light');
    if (btnDark && btnLight) {
        if (mode === 'dark') {
            btnDark.classList.add('active');
            btnLight.classList.remove('active');
        } else {
            btnDark.classList.remove('active');
            btnLight.classList.add('active');
        }
    }

    var quickBtn = document.getElementById('quick-mode-btn');
    if (quickBtn) {
        quickBtn.innerText = mode === 'dark' ? '🌙' : '☀️';
    }

    var tag = document.getElementById('theme-active-tag');
    if (tag) {
        var names = {
            'glass': 'Glass UI',
            'neumorphic': 'Neumorphism',
            'clay': 'Claymorphic',
            'dimensional': 'Dimensional',
            'hacker': 'Hacker UI'
        };
        var modeName = mode === 'dark' ? 'Dark' : 'Light';
        tag.innerText = (names[style] || style) + ' (' + modeName + ')';
    }
}

function changeThemeStyle(style) {
    var currentMode = localStorage.getItem('pc_controller_mode') || 'dark';
    applyTheme(style, currentMode);
}

function changeThemeMode(mode) {
    var currentStyle = localStorage.getItem('pc_controller_style') || 'glass';
    applyTheme(currentStyle, mode);
}

function toggleQuickMode() {
    var currentMode = localStorage.getItem('pc_controller_mode') || 'dark';
    var newMode = currentMode === 'dark' ? 'light' : 'dark';
    changeThemeMode(newMode);
}

// Auto-check authentication and initialize theme status on load
document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    fetch('/api/auth/check')
        .then(r => r.json())
        .then(d => {
            if (d.authenticated) {
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('main-app').style.display = 'block';
                initWebSocket();
            } else {
                document.getElementById('login-overlay').style.display = 'flex';
            }
        })
        .catch(() => {
            document.getElementById('login-overlay').style.display = 'flex';
        });
});

function sw(id, btn, title) { 
    document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active')); 
    document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active')); 
    document.getElementById(id).classList.add('active'); 
    btn.classList.add('active'); 
    document.getElementById('page-title').innerText = title; 
    if(id === 'files') listFiles(); 
}
function post(url, data) { fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
function shoot() { 
    if(liveMode) return; // Don't shoot if in live mode
    var txt = document.getElementById('ss-overlay'); 
    var img = document.getElementById('ss-img'); 
    txt.style.display = 'none'; 
    img.style.display = 'block'; 
    img.src = ''; 
    img.classList.remove('loaded'); 
    fetch('/api/screenshot').then(r=>r.json()).then(d=>{ 
        if(d.img) { img.src = 'data:image/jpeg;base64,' + d.img; img.classList.add('loaded'); } 
        else txt.style.display = 'flex'; 
    }); 
}
function setCircle(elementId, percentage) { 
    var el = document.getElementById(elementId); if(!el) return; 
    el.innerText = percentage + "%"; 
    var parent = el.parentElement; 
    var color = elementId === 'cpu-circle' ? '#8b5cf6' : '#06b6d4'; 
    parent.style.background = `conic-gradient(${color} ${percentage}%, rgba(255,255,255,0.05) 0%)`; 
}
setInterval(function(){ 
    fetch('/api/status').then(r=>r.json()).then(d=>{ 
        document.getElementById('active-app').innerText = "ACTIVE: " + (d.app.length > 25 ? d.app.substring(0,25)+'...' : d.app); 
        setCircle('cpu-circle', d.cpu); setCircle('ram-circle', d.ram); 
        var lockBtn = document.getElementById('btn-lock'); 
        if(d.mouse_locked){ lockBtn.innerText="🔒 Unlock Mouse"; lockBtn.classList.replace('btn-ghost','btn-danger'); } 
        else { lockBtn.innerText="🔓 Lock Mouse"; lockBtn.classList.replace('btn-danger','btn-ghost'); } 
    }); 
}, 2000);
function getClip() { 
    document.getElementById('pc-clip').innerText = 'Reading...'; 
    document.getElementById('btn-copy-mobile').style.display = 'none'; 
    fetch('/api/clipboard_get').then(r=>r.json()).then(d=>{ 
        var txt = d.text || "Clipboard Empty"; 
        document.getElementById('pc-clip').innerText = txt; 
        var copyBtn = document.getElementById('btn-copy-mobile'); 
        if (d.text && d.text.length > 0) { copyBtn.style.display = 'block'; } else { copyBtn.style.display = 'none'; } 
    }); 
}
function copyToClip() { 
    var txt = document.getElementById('pc-clip').innerText; 
    if (navigator.clipboard && window.isSecureContext) { 
        navigator.clipboard.writeText(txt).then(() => { 
            var btn = document.getElementById('btn-copy-mobile'); 
            var originalText = btn.innerText; 
            btn.innerText = "COPIED!"; 
            setTimeout(() => { btn.innerText = originalText; }, 1500); 
        }); 
    } else { alert("Manual copy required:\\n" + txt); } 
}
function sendClip() { post('/api/clipboard_send', {text: document.getElementById('send-clip').value}); }
function fileSelected() { 
    var file = document.getElementById('file-inp').files[0]; 
    if(file) { 
        document.getElementById('upload-area').style.display = 'block'; 
        document.getElementById('file-name').innerText = file.name;
        // Show file size
        var sizeEl = document.getElementById('file-size');
        if(sizeEl) {
            var size = file.size;
            var sizeStr = size < 1024 ? size + ' B' : 
                          size < 1048576 ? (size/1024).toFixed(1) + ' KB' : 
                          (size/1048576).toFixed(1) + ' MB';
            sizeEl.innerText = sizeStr;
        }
        document.getElementById('progress-container').style.display = 'none'; 
    } 
}

function uploadFile() { 
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
    xhr.upload.addEventListener("progress", function(evt) { 
        if (evt.lengthComputable) { 
            var now = Date.now();
            var loaded = evt.loaded;
            var total = evt.total;
            var percentComplete = Math.round(loaded / total * 100);
            
            // Update progress bar
            progressBar.style.width = percentComplete + "%";
            if(progressPercent) progressPercent.innerText = percentComplete + "%";
            
            // Calculate speed (bytes per second)
            var timeDiff = (now - lastTime) / 1000;
            if(timeDiff > 0.5) {  // Update every 0.5 seconds
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
            }
            
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
        } 
    }); 
    
    xhr.onload = function() { 
        if (this.status == 200) { 
            progressBar.style.width = "100%";
            if(progressPercent) progressPercent.innerText = "100%";
            if(uploadStatus) uploadStatus.innerText = "✅ Upload Complete!";
            if(uploadSpeed) uploadSpeed.innerText = "Done";
            if(uploadEta) uploadEta.innerText = "0s";
            
            setTimeout(function(){ 
                progressContainer.style.display = 'none'; 
                document.getElementById('upload-area').style.display = 'none';
                document.getElementById('file-inp').value = '';
            }, 3000); 
        } else { 
            if(uploadStatus) uploadStatus.innerText = "❌ Upload Failed";
            alert("Upload failed"); 
        } 
    }; 
    xhr.onerror = function() { 
        if(uploadStatus) uploadStatus.innerText = "❌ Upload Error";
        alert("Upload error"); 
    }; 
    xhr.open("POST", "/api/upload"); 
    xhr.send(fd); 
}

function listFiles() { 
    document.getElementById('flist').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);"><div style="font-size:24px;animation:pulse 1s infinite;">⏳</div>Loading files...</div>'; 
    fetch('/api/files_list').then(r=>r.json()).then(list=>{ 
        var html = ''; 
        if(list.length === 0) {
            html = '<div style="text-align:center;color:var(--text-muted);padding:30px;"><div style="font-size:32px;margin-bottom:10px;">📭</div>No files in Downloads folder</div>'; 
        } else {
            list.forEach(f=> { 
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
                
                html+='<div style="display:flex;justify-content:space-between;align-items:center;background:rgba(255,255,255,0.03);padding:12px 16px;border-radius:12px;margin-bottom:8px;border:1px solid var(--border);transition:all 0.2s;">';
                html+='<div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0;">';
                html+='<span style="font-size:24px;">'+icon+'</span>';
                html+='<span style="font-size:13px;color:var(--text-main);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+f+'</span>';
                html+='</div>';
                html+='<a href="/api/files_download/'+encodeURIComponent(f)+'" style="background:var(--primary);color:white;padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;">⬇️ Save</a>';
                html+='</div>'; 
            });
        }
        document.getElementById('flist').innerHTML = html; 
    }).catch(e=>{
        document.getElementById('flist').innerHTML = '<div style="text-align:center;color:var(--danger);padding:20px;">Error loading files</div>';
    });
}
function togglePrank(act, checkbox) { 
    var state = checkbox.checked ? 'on' : 'off'; 
    var speed = document.getElementById('speed-screen') ? document.getElementById('speed-screen').value : 'NORMAL'; 
    post('/api/prank', {action: act, state: state, speed: speed}); 
}

// Matrix Rain with color and length options
function toggleMatrixRain(checkbox) {
    var state = checkbox.checked ? 'on' : 'off';
    var speed = document.getElementById('speed-screen').value || 'NORMAL';
    var color = document.getElementById('matrix-color').value || 'green';
    var length = document.getElementById('matrix-length').value || 'medium';
    post('/api/prank', {action: 'matrix', state: state, speed: speed, color: color, length: length});
}

// Toggle input blocking (real mouse/keyboard lock)
function toggleInputBlock(target, checkbox) {
    var act = checkbox.checked ? 'on' : 'off';
    post('/api/input_block', {action: act, target: target});
}

// Matrix Image - stored file data
var matrixImageFile = null;

// Handle Matrix image upload
function handleMatrixUpload() {
    var inp = document.getElementById('matrix-img-input');
    if(inp.files.length === 0) return;
    
    matrixImageFile = inp.files[0];
    
    // Show controls, hide upload zone
    document.getElementById('matrix-upload-zone').style.display = 'none';
    document.getElementById('matrix-controls').style.display = 'block';
    document.getElementById('matrix-filename').innerText = matrixImageFile.name;
    document.getElementById('chk-matrix-display').checked = false;
}

// Toggle Matrix display on/off
function toggleMatrixDisplay(checkbox) {
    if(!matrixImageFile) {
        checkbox.checked = false;
        return;
    }
    
    if(checkbox.checked) {
        // Upload and display
        var fd = new FormData();
        fd.append('file', matrixImageFile);
        fetch('/api/matrix_image', {method:'POST', body: fd})
            .then(r => r.json())
            .then(data => {
                if(data.status !== 'displaying') {
                    checkbox.checked = false;
                }
            });
    } else {
        // Close the display
        post('/api/matrix_close', {});
    }
}

// Replace Matrix image - go back to upload zone
function replaceMatrixImage() {
    matrixImageFile = null;
    document.getElementById('matrix-upload-zone').style.display = 'block';
    document.getElementById('matrix-controls').style.display = 'none';
    document.getElementById('chk-matrix-display').checked = false;
    document.getElementById('matrix-img-input').value = '';
}

// Check for updates
function checkForUpdates() {
    document.getElementById('btn-check-update').disabled = true;
    document.getElementById('update-checking').style.display = 'block';
    document.getElementById('update-status').style.display = 'none';
    document.getElementById('update-uptodate').style.display = 'none';
    document.getElementById('btn-restart').style.display = 'none';
    
    fetch('/api/check_update')
        .then(r => r.json())
        .then(data => {
            document.getElementById('update-checking').style.display = 'none';
            document.getElementById('btn-check-update').disabled = false;
            
            if(data.status === 'error') {
                alert('Error checking for updates: ' + data.message);
                return;
            }
            
            if(data.update_available) {
                document.getElementById('new-version').innerText = 'v' + data.remote_version;
                document.getElementById('update-status').style.display = 'block';
                document.getElementById('btn-restart').style.display = 'block';
            } else {
                document.getElementById('update-uptodate').style.display = 'block';
            }
        })
        .catch(e => {
            document.getElementById('update-checking').style.display = 'none';
            document.getElementById('btn-check-update').disabled = false;
            alert('Failed to check for updates');
        });
}

// Restart Controller with new version
function restartController() {
    if(!confirm('Restart PC Controller now?')) return;
    
    document.getElementById('btn-restart').disabled = true;
    document.getElementById('btn-restart').innerText = '⏳ Restarting...';
    
    fetch('/api/restart', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})})
        .then(r => r.json())
        .then(data => {
            if(data.status === 'restarting') {
                document.getElementById('btn-restart').innerText = '✅ Restarted! Refresh page...';
                setTimeout(() => { location.reload(); }, 3000);
            }
        })
        .catch(e => {
            document.getElementById('btn-restart').disabled = false;
            document.getElementById('btn-restart').innerText = '🔄 Restart with New Version';
        });
}

// ============ V2.4.0 NEW FEATURES ============

// --- Load App Data (called when Apps tab opens) ---
function loadAppData() {
    loadApps();
    loadWindows();
    loadProcesses();
    browseHome();
}

// --- App Launcher ---
function loadApps() {
    fetch('/api/apps').then(r=>r.json()).then(data => {
        var html = '';
        if(data.apps && data.apps.length > 0) {
            data.apps.forEach(app => {
                var icon = app.icon || '📦';
                if(app.icon && app.icon.startsWith('data:')) {
                    icon = '<img src="'+app.icon+'" style="width:32px;height:32px;border-radius:6px;">';
                }
                html += `<div onclick="launchApp('${app.path.replace(/\\/g,'\\\\')}')" style="text-align:center;padding:12px;background:rgba(255,255,255,0.03);border-radius:12px;cursor:pointer;border:1px solid var(--border);">`;
                html += '<div style="font-size:28px;">'+icon+'</div>';
                html += '<div style="font-size:11px;color:var(--text-muted);margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+app.name+'</div>';
                html += '</div>';
            });
        } else {
            html = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:20px;">No apps added yet</div>';
        }
        document.getElementById('app-grid').innerHTML = html;
    });
}

function launchApp(path) {
    post('/api/launch_app', {path: path});
}

function addNewApp() {
    var name = document.getElementById('app-name').value;
    var path = document.getElementById('app-path').value;
    if(!name || !path) { alert('Enter app name and path'); return; }
    
    fetch('/api/add_app', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:name, path:path})})
        .then(r=>r.json())
        .then(data => {
            document.getElementById('app-name').value = '';
            document.getElementById('app-path').value = '';
            loadApps();
        });
}

// --- Window Manager ---
function loadWindows() {
    document.getElementById('window-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/windows').then(r=>r.json()).then(data => {
        var html = '';
        if(data.windows && data.windows.length > 0) {
            data.windows.forEach(w => {
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;background:rgba(255,255,255,0.03);border-radius:8px;margin-bottom:6px;border:1px solid var(--border);">';
                html += '<div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;">'+w.title+'</div>';
                html += '<div style="display:flex;gap:5px;">';
                html += '<button onclick="focusWin('+w.hwnd+')" style="padding:5px 10px;background:var(--primary);color:white;border:none;border-radius:6px;font-size:10px;cursor:pointer;">Switch</button>';
                html += '<button onclick="closeWin('+w.hwnd+')" style="padding:5px 10px;background:var(--danger);color:white;border:none;border-radius:6px;font-size:10px;cursor:pointer;">✕</button>';
                html += '</div></div>';
            });
        } else {
            html = '<div style="text-align:center;color:var(--text-muted);padding:20px;">No windows found</div>';
        }
        document.getElementById('window-list').innerHTML = html;
    });
}

function focusWin(hwnd) { post('/api/focus_window', {hwnd: hwnd}); }
function closeWin(hwnd) { post('/api/close_window', {hwnd: hwnd}); loadWindows(); }

// --- Task Manager ---
function loadProcesses() {
    document.getElementById('process-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/processes').then(r=>r.json()).then(data => {
        var html = '';
        if(data.processes && data.processes.length > 0) {
            data.processes.forEach(p => {
                html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:rgba(255,255,255,0.02);border-radius:6px;margin-bottom:4px;font-size:11px;">';
                html += '<div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+p.name+'</div>';
                html += '<div style="color:var(--text-muted);margin:0 10px;">'+p.memory_mb+' MB</div>';
                html += '<button onclick="killProc('+p.pid+')" style="padding:4px 8px;background:var(--danger);color:white;border:none;border-radius:4px;font-size:10px;cursor:pointer;">Kill</button>';
                html += '</div>';
            });
        }
        document.getElementById('process-list').innerHTML = html;
    });
}

function killProc(pid) {
    if(!confirm('Kill this process?')) return;
    fetch('/api/kill_process', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({pid:pid})})
        .then(r=>r.json()).then(data => { loadProcesses(); });
}

// --- Voice Commands ---
var recognition = null;
function startVoice() {
    if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Voice not supported in this browser');
        return;
    }
    
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = document.getElementById('voice-lang').value;
    recognition.continuous = false;
    
    document.getElementById('voice-status').innerText = '🔴 Listening...';
    document.getElementById('voice-btn').style.background = 'var(--danger)';
    
    recognition.onresult = function(event) {
        var cmd = event.results[0][0].transcript;
        document.getElementById('voice-result').innerText = '"' + cmd + '"';
        document.getElementById('voice-status').innerText = 'Processing...';
        
        fetch('/api/voice_command', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:cmd})})
            .then(r=>r.json()).then(data => {
                if(data.status === 'ok') {
                    document.getElementById('voice-status').innerText = '✅ ' + (data.action || 'Done');
                } else if(data.status === 'confirm') {
                    if(confirm(data.message)) {
                        post('/api/action', {action: data.action, password: prompt('Admin password:')});
                    }
                    document.getElementById('voice-status').innerText = 'Tap mic and speak';
                } else {
                    document.getElementById('voice-status').innerText = '❓ Command not recognized';
                }
            });
    };
    
    recognition.onerror = function(event) {
        document.getElementById('voice-status').innerText = '❌ Error: ' + event.error;
        document.getElementById('voice-btn').style.background = '';
    };
    
    recognition.onend = function() {
        document.getElementById('voice-btn').style.background = '';
    };
    
    recognition.start();
}

// --- Scheduled Tasks ---
function scheduleIn(seconds) {
    var action = document.getElementById('sched-action').value;
    fetch('/api/schedule', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:action, delay:seconds})})
        .then(r=>r.json()).then(data => {
            if(data.status === 'ok') {
                document.getElementById('active-schedules').innerText = '⏰ '+action+' scheduled in ' + Math.floor(seconds/60) + ' minutes';
            }
        });
}

// --- File Browser ---
var currentBrowsePath = '';
function browseHome() { browseTo(''); }
function browseParent() { 
    if(currentBrowsePath) {
        var parent = currentBrowsePath.split(/[\\\\/]/).slice(0,-1).join('\\\\');
        browseTo(parent || '');
    }
}

function browseTo(path) {
    currentBrowsePath = path;
    document.getElementById('browse-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</div>';
    fetch('/api/browse?path=' + encodeURIComponent(path)).then(r=>r.json()).then(data => {
        if(data.status === 'error') {
            document.getElementById('browse-list').innerHTML = '<div style="color:var(--danger);padding:20px;">'+data.message+'</div>';
            return;
        }
        document.getElementById('browse-path').innerText = data.path;
        currentBrowsePath = data.path;
        
        var html = '';
        data.items.forEach(item => {
            var icon = item.is_dir ? '📁' : '📄';
            var targetPath = item.path.replace(/\\/g, '\\\\');
            var actionCall = item.is_dir ? `browseTo('${targetPath}')` : `openBrowseFile('${targetPath}')`;
            html += `<div onclick="${actionCall}" style="display:flex;align-items:center;gap:10px;padding:10px;background:rgba(255,255,255,0.02);border-radius:8px;margin-bottom:4px;cursor:pointer;border:1px solid var(--border);">`;
            html += '<span style="font-size:20px;">'+icon+'</span>';
            html += '<span style="flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+item.name+'</span>';
            if(!item.is_dir) html += '<span style="font-size:10px;color:var(--text-muted);">'+(item.size/1024).toFixed(1)+' KB</span>';
            html += '</div>';
        });
        document.getElementById('browse-list').innerHTML = html || '<div style="text-align:center;color:var(--text-muted);padding:20px;">Empty folder</div>';
    });
}

function openBrowseFile(path) {
    post('/api/open_file', {path: path});
}

// --- Live Screen Mirror ---
var mirrorActive = false;
function toggleScreenMirror() {
    mirrorActive = !mirrorActive;
    var btn = document.getElementById('stream-btn');
    var container = document.getElementById('mirror-container');
    var img = document.getElementById('mirror-img');
    
    if(mirrorActive) {
        var fps = document.getElementById('stream-fps').value;
        img.src = '/api/screen_stream?fps=' + fps + '&quality=40';
        container.style.display = 'block';
        btn.innerText = '⏹️ Stop Mirror';
        btn.style.background = 'var(--danger)';
    } else {
        img.src = '';
        container.style.display = 'none';
        btn.innerText = '▶️ Start Mirror';
        btn.style.background = '';
    }
}

function fullscreenMirror() {
    var img = document.getElementById('mirror-img');
    if(img.requestFullscreen) img.requestFullscreen();
    else if(img.webkitRequestFullscreen) img.webkitRequestFullscreen();
}

// ============ END V2.4.0 ============

function doAction(act) { 
    var p = prompt("Enter Admin Password"); 
    if(p) post('/api/action', {action:act, password:p}); 
}
function runCmd() { 
    var p = prompt("Enter Admin Password"); 
    if(p) { 
        var cmd = document.getElementById('cmd-input').value; 
        document.getElementById('cmd-out').innerText = "Running..."; 
        fetch('/api/exec', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cmd:cmd, password:p})}).then(r=>r.json()).then(d=>{ document.getElementById('cmd-out').innerText = d.output || d.status; }); 
    } 
}
function openUrl() { var url = document.getElementById('url-input').value; if(url) post('/api/open_url', {url:url}); }
function toggleLock() { post('/api/media', {action:'lock_mouse'}); }

// --- NEW: System Info ---
function loadSysInfo() {
    fetch('/api/sysinfo').then(r=>r.json()).then(d=>{
        if(d.error) return;
        document.getElementById('sys-cpu-cores').innerText = d.cpu_cores;
        document.getElementById('sys-ram').innerText = d.ram_used_gb + '/' + d.ram_total_gb;
        document.getElementById('sys-disk').innerText = d.disk_used_gb + '/' + d.disk_total_gb;
        document.getElementById('sys-uptime').innerText = d.uptime;
    });
}

// --- NEW: Check for Updates ---
function checkForUpdate() {
    var btn = event.target;
    btn.innerText = 'Checking...';
    fetch('/api/check_update', {method:'POST'}).then(r=>r.json()).then(d=>{
        if(d.updated) {
            btn.innerText = '✅ Updated!';
            alert('Update downloaded! Please restart PC Controller.');
        } else {
            btn.innerText = '✅ Up to date!';
        }
        setTimeout(()=>{ btn.innerText = '🔄 Check for Updates'; }, 3000);
    }).catch(()=>{
        btn.innerText = '❌ Error';
        setTimeout(()=>{ btn.innerText = '🔄 Check for Updates'; }, 3000);
    });
}

// --- NEW: Power Actions with Password ---
function doPower(act) {
    var p = prompt("Enter Admin Password");
    if(p) post('/api/power', {action:act, password:p});
}

// --- LOW-LATENCY TRACKPAD WITH WEBSOCKET EMIT ---
var sx, sy;
var pad = document.getElementById('pad'); 
if (pad) {
    pad.addEventListener('touchstart', function(e) { 
        sx = e.touches[0].clientX; 
        sy = e.touches[0].clientY; 
    }, {passive: true}); 

    pad.addEventListener('touchmove', function(e) { 
        e.preventDefault(); 
        var dx = (e.touches[0].clientX - sx) * 2.0; 
        var dy = (e.touches[0].clientY - sy) * 2.0; 
        
        if (socket && socket.connected) {
            socket.emit('mouse_rel', {x: dx, y: dy});
        } else {
            post('/api/mouse_rel', {x: dx, y: dy});
        }
        
        sx = e.touches[0].clientX; 
        sy = e.touches[0].clientY; 
    }, {passive: false});

    // Tap on trackpad triggers left click
    var touchStartTime = 0;
    pad.addEventListener('touchstart', function(e) {
        touchStartTime = Date.now();
    }, {passive: true});

    pad.addEventListener('touchend', function(e) {
        if (Date.now() - touchStartTime < 200) {
            if (navigator.vibrate) navigator.vibrate(15);
            if (socket && socket.connected) {
                socket.emit('mouse_click', {btn: 'left'});
            } else {
                post('/api/mouse_click', {btn: 'left'});
            }
        }
    });
}