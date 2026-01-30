"""
PC Controller - Simple Popup
Shows a message with a Copy button. Click to copy and close.
"""
import tkinter as tk
import sys

try:
    import pyperclip
except:
    pyperclip = None

def show_popup(message):
    root = tk.Tk()
    root.title("PC Controller")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.configure(bg='#1a1a2e')
    
    # Size and position
    width, height = 400, 220
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Border frame
    border = tk.Frame(root, bg='#8b5cf6')
    border.pack(fill='both', expand=True)
    
    main = tk.Frame(border, bg='#1a1a2e')
    main.pack(fill='both', expand=True, padx=3, pady=3)
    
    # Message
    tk.Label(
        main,
        text=message,
        font=('Segoe UI', 13),
        fg='#ffffff',
        bg='#1a1a2e',
        wraplength=350,
        justify='center'
    ).pack(fill='both', expand=True, padx=20, pady=20)
    
    # Copy button
    def copy_close():
        if pyperclip:
            try:
                pyperclip.copy(message)
            except:
                pass
        root.destroy()
    
    btn = tk.Button(
        main,
        text="📋  Copy",
        font=('Segoe UI', 12, 'bold'),
        fg='#ffffff',
        bg='#8b5cf6',
        activebackground='#a78bfa',
        activeforeground='#ffffff',
        relief='flat',
        cursor='hand2',
        command=copy_close,
        pady=12
    )
    btn.pack(fill='x', padx=20, pady=(0, 20))
    
    root.bind('<Escape>', lambda e: root.destroy())
    root.bind('<Return>', lambda e: copy_close())
    root.after(60000, root.destroy)
    
    root.mainloop()

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Test message"
    show_popup(msg)
