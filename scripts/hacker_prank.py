"""
PC Controller - Hacker Typer Prank
Realistic hacking simulation with code, terminals, progress bars, and visual effects.
"""
import tkinter as tk
import random
import sys
import ctypes
import time

SPEED_MODE = sys.argv[1] if len(sys.argv) > 1 else "FAST"
user32 = ctypes.windll.user32

def hide_taskbar():
    try:
        user32.ShowWindow(user32.FindWindow("Shell_TrayWnd", None), 0)
        user32.ShowWindow(user32.FindWindow("Button", None), 0)
    except: pass

def show_taskbar():
    try:
        user32.ShowWindow(user32.FindWindow("Shell_TrayWnd", None), 5)
        user32.ShowWindow(user32.FindWindow("Button", None), 1)
    except: pass

# Real-looking code snippets
CODE_SNIPPETS = [
    # Python exploitation
    "import socket, subprocess, os",
    "def exploit_target(ip, port):",
    "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)",
    "    s.connect((ip, port))",
    "    payload = generate_shellcode()",
    "    s.send(payload.encode())",
    "    return s.recv(4096)",
    "",
    "# Bypass authentication module",
    "class AuthBypass:",
    "    def __init__(self, target):",
    "        self.target = target",
    "        self.session = None",
    "    ",
    "    def inject_credentials(self, token):",
    "        headers = {'Authorization': f'Bearer {token}'}",
    "        return requests.post(self.target, headers=headers)",
    "",
    "# Network scanner",
    "def scan_network(subnet):",
    "    active_hosts = []",
    "    for i in range(1, 255):",
    "        ip = f'{subnet}.{i}'",
    "        if ping(ip): active_hosts.append(ip)",
    "    return active_hosts",
    "",
    "# Encryption breaker",
    "def decrypt_aes256(ciphertext, key_fragment):",
    "    key = bruteforce_key(key_fragment)",
    "    cipher = AES.new(key, AES.MODE_CBC)",
    "    return cipher.decrypt(ciphertext)",
    "",
    "# SQL injection payload",
    "payload = \"' OR '1'='1'; DROP TABLE users; --\"",
    "cursor.execute(f'SELECT * FROM users WHERE id={payload}')",
]

HACK_MESSAGES = [
    "[*] Initiating connection to target...",
    "[+] Connection established",
    "[*] Scanning for vulnerabilities...",
    "[+] Found open port: 22 (SSH)",
    "[+] Found open port: 80 (HTTP)",
    "[+] Found open port: 443 (HTTPS)",
    "[!] Vulnerability detected: CVE-2024-1234",
    "[*] Exploiting vulnerability...",
    "[+] Exploit successful! Gaining access...",
    "[*] Elevating privileges...",
    "[+] ROOT ACCESS GRANTED",
    "[*] Dumping password hashes...",
    "[+] Retrieved 1,247 password hashes",
    "[*] Cracking passwords with hashcat...",
    "[*] Extracting sensitive files...",
    "[+] Downloaded: financial_records.xlsx",
    "[+] Downloaded: customer_database.sql",
    "[*] Installing backdoor...",
    "[+] Backdoor installed successfully",
    "[*] Covering tracks...",
    "[+] Logs cleared",
    "[!] INTRUSION COMPLETE",
]

class HackerScreen:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='#0a0a0a')
        hide_taskbar()
        
        self.force_focus()
        self.root.bind("<Any-KeyPress>", lambda e: "break")
        self.root.bind("<Button-1>", lambda e: "break")
        
        self.setup_ui()
        self.line_index = 0
        self.start_hacking()
        
    def setup_ui(self):
        # Header with "hacking" status
        header = tk.Frame(self.root, bg='#0a0a0a')
        header.pack(fill='x', padx=10, pady=5)
        
        self.status_label = tk.Label(
            header,
            text="[SYSTEM BREACH IN PROGRESS]",
            font=('Consolas', 12, 'bold'),
            fg='#ff0000',
            bg='#0a0a0a'
        )
        self.status_label.pack(side='left')
        
        self.target_label = tk.Label(
            header,
            text=f"TARGET: {random.randint(10,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            font=('Consolas', 12),
            fg='#00ff00',
            bg='#0a0a0a'
        )
        self.target_label.pack(side='right')
        
        # Main terminal
        main_frame = tk.Frame(self.root, bg='#0a0a0a')
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left side - code
        left_frame = tk.Frame(main_frame, bg='#1a1a1a', highlightbackground='#333', highlightthickness=1)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0,5))
        
        tk.Label(left_frame, text=" PAYLOAD INJECTOR ", font=('Consolas', 10, 'bold'), 
                 fg='#00ff00', bg='#1a1a1a').pack(anchor='w', padx=5, pady=2)
        
        self.code_area = tk.Text(left_frame, bg='#0d0d0d', fg='#00ff00', 
                                  font=('Consolas', 11), wrap='none', state='normal',
                                  insertbackground='#00ff00')
        self.code_area.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Right side - logs
        right_frame = tk.Frame(main_frame, bg='#1a1a1a', highlightbackground='#333', highlightthickness=1)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5,0))
        
        tk.Label(right_frame, text=" SYSTEM LOGS ", font=('Consolas', 10, 'bold'),
                 fg='#ffaa00', bg='#1a1a1a').pack(anchor='w', padx=5, pady=2)
        
        self.log_area = tk.Text(right_frame, bg='#0d0d0d', fg='#aaaaaa',
                                 font=('Consolas', 10), wrap='word', state='normal')
        self.log_area.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure log colors
        self.log_area.tag_config('success', foreground='#00ff00')
        self.log_area.tag_config('warning', foreground='#ffaa00')
        self.log_area.tag_config('error', foreground='#ff0000')
        self.log_area.tag_config('info', foreground='#00aaff')
        
        # Bottom progress bar
        bottom = tk.Frame(self.root, bg='#0a0a0a')
        bottom.pack(fill='x', padx=10, pady=5)
        
        tk.Label(bottom, text="BREACH PROGRESS:", font=('Consolas', 10),
                 fg='#888', bg='#0a0a0a').pack(side='left')
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_canvas = tk.Canvas(bottom, height=20, bg='#1a1a1a', highlightthickness=0)
        self.progress_canvas.pack(side='left', fill='x', expand=True, padx=10)
        
        self.progress_label = tk.Label(bottom, text="0%", font=('Consolas', 10, 'bold'),
                                        fg='#00ff00', bg='#0a0a0a')
        self.progress_label.pack(side='right')
        
    def force_focus(self):
        try:
            self.root.focus_force()
            self.root.lift()
            self.root.after(50, self.force_focus)
        except: pass
        
    def get_delay(self):
        delays = {"INSANE": (1, 10), "FAST": (10, 30), "NORMAL": (30, 60), "LAGGY": (80, 150)}
        min_d, max_d = delays.get(SPEED_MODE, (30, 60))
        return random.randint(min_d, max_d)
    
    def start_hacking(self):
        self.code_index = 0
        self.log_index = 0
        self.progress = 0
        self.type_code()
        self.root.after(500, self.add_log)
        self.root.after(200, self.update_progress)
        self.root.after(1000, self.blink_status)
        
    def type_code(self):
        if self.code_index < len(CODE_SNIPPETS):
            line = CODE_SNIPPETS[self.code_index]
            self.code_area.insert(tk.END, line + "\n")
            self.code_area.see(tk.END)
            self.code_index += 1
            
            # Add some hex output occasionally
            if random.random() < 0.15:
                hex_line = "  >>> " + " ".join([f"{random.randint(0,255):02X}" for _ in range(16)])
                self.code_area.insert(tk.END, hex_line + "\n")
                
        else:
            self.code_index = 0
            
        self.root.after(self.get_delay() * 3, self.type_code)
        
    def add_log(self):
        if self.log_index < len(HACK_MESSAGES):
            msg = HACK_MESSAGES[self.log_index]
            
            # Determine color tag
            if msg.startswith("[+]"):
                tag = 'success'
            elif msg.startswith("[!]"):
                tag = 'error'
            elif msg.startswith("[*]"):
                tag = 'info'
            else:
                tag = 'warning'
                
            timestamp = time.strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
            self.log_area.see(tk.END)
            self.log_index += 1
        else:
            self.log_index = 0
            
        self.root.after(random.randint(800, 2000), self.add_log)
        
    def update_progress(self):
        if self.progress < 100:
            self.progress += random.uniform(0.1, 0.5)
            self.progress = min(100, self.progress)
            
            # Draw progress bar
            self.progress_canvas.delete('all')
            width = self.progress_canvas.winfo_width()
            fill_width = int(width * self.progress / 100)
            
            # Gradient effect
            color = '#00ff00' if self.progress < 75 else '#ffaa00' if self.progress < 95 else '#ff0000'
            self.progress_canvas.create_rectangle(0, 0, fill_width, 20, fill=color, outline='')
            
            self.progress_label.config(text=f"{self.progress:.1f}%")
            
        self.root.after(100, self.update_progress)
        
    def blink_status(self):
        current = self.status_label.cget('fg')
        new_color = '#ff0000' if current == '#0a0a0a' else '#0a0a0a'
        self.status_label.config(fg=new_color)
        self.root.after(500, self.blink_status)

try:
    root = tk.Tk()
    app = HackerScreen(root)
    root.mainloop()
finally:
    show_taskbar()