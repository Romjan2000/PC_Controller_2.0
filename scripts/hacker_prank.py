import tkinter as tk
import random
import sys
import ctypes

if len(sys.argv) > 1:
    SPEED_MODE = sys.argv[1]
else:
    SPEED_MODE = "INSANE"

user32 = ctypes.windll.user32

def hide_taskbar():
    try:
        user32.ShowWindow(user32.FindWindow("Shell_TrayWnd", None), 0)
        user32.ShowWindow(user32.FindWindow("Button", None), 0) 
    except:
        pass

def show_taskbar():
    try:
        user32.ShowWindow(user32.FindWindow("Shell_TrayWnd", None), 5)
        user32.ShowWindow(user32.FindWindow("Button", None), 1)
    except:
        pass

class HackerScreen:
    def __init__(self, root):
        self.root = root
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='black')
        
        hide_taskbar()

        self.force_focus()
        self.root.bind("<Any-KeyPress>", lambda e: "break")

        self.lines = self.generate_hacker_lines(5000)
        self.line_index = 0
        
        self.text_area = tk.Text(root, bg='black', fg='#00FF41', font=('Consolas', 14), wrap='none', state='normal')
        self.text_area.pack(fill='both', expand=True)
        self.text_area.configure(insertbackground='black') 

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.type_next_line()

    def on_close(self):
        show_taskbar()
        self.root.destroy()

    def force_focus(self):
        try:
            self.root.focus_force()
            self.root.lift()
            self.root.after(50, self.force_focus)
        except:
            pass

    def generate_hex(self, length): 
        return ''.join(random.choices("0123456789ABCDEF", k=length))

    def generate_progress_bar(self):
        percent = random.randint(0, 100)
        filled = int(percent / 5)
        bar = "█" * filled + "░" * (20 - filled)
        return f"[{bar}] {percent}%"

    def generate_hacker_lines(self, num_lines):
        file_names = ["sys_core.dump", "kernel_config.dat", "user_passwords.db", "network_log.enc"]
        processes = ["initiating_handshake", "bypassing_firewall", "injecting_sql_payload"]
        generated = []
        for i in range(num_lines):
            line_style = random.choice(['matrix', 'status', 'directory', 'hex_dump'])
            if line_style == 'matrix':
                line = f"0x{self.generate_hex(4)}  {random.randint(1000,9999)}  {self.generate_hex(8)} :: {random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
            elif line_style == 'status':
                action = random.choice(processes).upper()
                target = random.choice(file_names)
                bar = self.generate_progress_bar()
                line = f"{action} > {target} {bar}"
            elif line_style == 'directory':
                line = f"root@system:~/src/dir_{random.randint(10,99)}$ cat {random.choice(file_names)}"
            elif line_style == 'hex_dump':
                offset = f"{i*16:08x}"
                bytes_str = " ".join([self.generate_hex(2) for _ in range(8)])
                line = f"{offset}  {bytes_str}"
            generated.append(line + "\n")
        return generated

    def get_delay(self):
        if SPEED_MODE == "INSANE": return random.randint(1, 5)
        elif SPEED_MODE == "FAST": return random.randint(10, 20)
        elif SPEED_MODE == "NORMAL": return random.randint(25, 40)
        else: return random.randint(60, 100)  # LAGGY mode

    def type_next_line(self):
        if self.line_index < len(self.lines):
            current_text = self.lines[self.line_index].strip()
            self.char_index = 0
            self.typewriter(current_text)
        else:
            self.line_index = 0
            self.type_next_line()

    def typewriter(self, text):
        if self.char_index < len(text):
            char = text[self.char_index]
            self.text_area.insert(tk.END, char)
            self.char_index += 1
            delay = self.get_delay()
            self.root.after(delay, lambda: self.typewriter(text))
        else:
            self.text_area.insert(tk.END, "\n")
            self.text_area.see(tk.END)
            self.line_index += 1
            self.root.after(10, self.type_next_line)

try:
    root = tk.Tk()
    app = HackerScreen(root)
    root.mainloop()
finally:
    show_taskbar()