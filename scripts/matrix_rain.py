import tkinter as tk
import random
import sys
import ctypes

if len(sys.argv) > 1:
    SPEED_MODE = sys.argv[1]
else:
    SPEED_MODE = "FAST"

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

def get_speed_settings():
    if SPEED_MODE == "LAGGY": DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = 1, 100, 0.05
    elif SPEED_MODE == "NORMAL": DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = 3, 30, 0.25
    elif SPEED_MODE == "FAST": DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = 6, 15, 0.4
    elif SPEED_MODE == "INSANE": DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = 10, 5, 0.6
    else: DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = 3, 30, 0.25
    return DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE

DROP_SPEED, REFRESH_RATE, SPAWN_CHANCE = get_speed_settings()
NUM_COLUMNS = 100

try:
    root = tk.Tk()
    root.attributes('-fullscreen', True, '-topmost', True)
    root.configure(bg='black')

    hide_taskbar()

    def block_input(event): return "break"
    root.bind("<Any-KeyPress>", block_input)
    root.bind("<Button-1>", block_input)

    def force_focus():
        root.focus_force()
        root.lift()
        root.after(50, force_focus)
    force_focus()

    c = tk.Canvas(root, bg='black', highlightthickness=0)
    c.pack(fill='both', expand=True)

    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    drops = []

    def update():
        if len(drops) < NUM_COLUMNS and random.random() < SPAWN_CHANCE:
            x = random.randint(0, w)
            char = random.choice("0123456789ABCDEF")
            item = c.create_text(x, 0, text=char, fill='#0F0', font=('Consolas', 16, 'bold'))
            drops.append(item)
        
        to_remove = []
        for item in drops:
            c.move(item, 0, DROP_SPEED)
            coords = c.coords(item)
            if coords and coords[1] > h:
                to_remove.append(item)
        
        for item in to_remove:
            c.delete(item)
            drops.remove(item)
            
        root.after(REFRESH_RATE, update)

    update()
    root.mainloop()
finally:
    show_taskbar()