import tkinter as tk
import sys
try:
    import pyperclip
except:
    pyperclip = None

def run_popup(msg):
    try:
        root = tk.Tk()
        root.title("Note")
        root.attributes('-topmost', True)
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        w, h = 400, 150
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        root.configure(bg="#1e1e2e")
        root.overrideredirect(True)
        
        root.after(100, root.focus_force)
        root.grab_set()
        
        def copy_text():
            if pyperclip:
                pyperclip.copy(msg)
        
        def close_popup():
            root.destroy()
        
        def copy_and_close():
            copy_text()
            close_popup()
            
        tk.Label(root, text="📌 MESSAGE", bg="#1e1e2e", fg="#00ff88", font=("Segoe UI", 10, "bold")).pack(pady=8)
        tk.Label(root, text=msg, wraplength=300, bg="#1e1e2e", fg="white", font=("Segoe UI", 11)).pack(expand=True)
        
        # Button frame for multiple buttons
        btn_frame = tk.Frame(root, bg="#1e1e2e")
        btn_frame.pack(pady=8)
        
        tk.Button(btn_frame, text="📋 COPY & CLOSE", command=copy_and_close, bg="#00ff88", fg="black", relief="flat", font=("Segoe UI", 10, "bold"), padx=15, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ CLOSE", command=close_popup, bg="#ff5555", fg="white", relief="flat", font=("Segoe UI", 10, "bold"), padx=15, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        root.after(15000, root.destroy) 
        root.mainloop()
    except:
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_popup(sys.argv[1])