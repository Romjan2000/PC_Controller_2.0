import tkinter as tk
import ctypes
import sys

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

def block_key(event):
    # Allow ESC key to close the prank
    if event.keysym == 'Escape':
        show_taskbar()
        root.destroy()
        return
    return "break"

try:
    root = tk.Tk()
    root.title("")
    root.attributes('-fullscreen', True, '-topmost', True)
    root.attributes('-disabled', True)
    root.configure(bg='#0078D7')

    hide_taskbar()
    root.bind("<Any-KeyPress>", block_key)

    def force_focus():
        root.focus_force()
        root.lift()
        root.after(50, force_focus)
    force_focus()

    tk.Label(root, text=":(\n\nYour PC ran into a problem and needs to restart.\nWe're just collecting some error info, and then we'll restart for you.\n\n0% complete", fg='white', bg='#0078D7', font=('Segoe UI', 24)).pack(expand=True)

    root.mainloop()
finally:
    # CRITICAL FIX: Always restore taskbar even if script crashes
    show_taskbar()