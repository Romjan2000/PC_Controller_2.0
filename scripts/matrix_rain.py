"""
PC Controller - Matrix Rain Effect
Classic Matrix digital rain with customizable colors and trail lengths.
Usage: python matrix_rain.py [SPEED] [COLOR] [LENGTH]
  SPEED: LAGGY, NORMAL, FAST, INSANE
  COLOR: green, blue, red, purple, cyan, rainbow, multi
  LENGTH: short, medium, long
"""
import tkinter as tk
import random
import sys
import ctypes

# Parse arguments
SPEED_MODE = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
COLOR_MODE = sys.argv[2] if len(sys.argv) > 2 else "green"
LENGTH_MODE = sys.argv[3] if len(sys.argv) > 3 else "medium"

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

def get_speed_settings():
    settings = {
        "LAGGY":  (1, 80, 0.03),
        "NORMAL": (2, 40, 0.08),
        "FAST":   (4, 25, 0.15),
        "INSANE": (6, 15, 0.25)
    }
    return settings.get(SPEED_MODE, settings["NORMAL"])

def get_length_settings():
    lengths = {
        "short": (5, 10),
        "medium": (10, 18),
        "long": (18, 30)
    }
    return lengths.get(LENGTH_MODE, lengths["medium"])

# Color palettes with fading shades
COLOR_PALETTES = {
    "green": [
        "#ffffff", "#00ff00", "#00dd00", "#00bb00", "#009900",
        "#007700", "#005500", "#004400", "#003300", "#002200", "#001500"
    ],
    "blue": [
        "#ffffff", "#00aaff", "#0099ee", "#0088dd", "#0077cc",
        "#0066aa", "#005588", "#004466", "#003355", "#002244", "#001133"
    ],
    "red": [
        "#ffffff", "#ff3333", "#ee2222", "#dd1111", "#cc0000",
        "#aa0000", "#880000", "#660000", "#550000", "#440000", "#330000"
    ],
    "purple": [
        "#ffffff", "#cc66ff", "#bb55ee", "#aa44dd", "#9933cc",
        "#8822aa", "#771188", "#660066", "#550055", "#440044", "#330033"
    ],
    "cyan": [
        "#ffffff", "#00ffff", "#00dddd", "#00bbbb", "#009999",
        "#007777", "#006666", "#005555", "#004444", "#003333", "#002222"
    ],
    "yellow": [
        "#ffffff", "#ffff00", "#eeee00", "#dddd00", "#cccc00",
        "#aaaa00", "#888800", "#666600", "#555500", "#444400", "#333300"
    ],
    "pink": [
        "#ffffff", "#ff66aa", "#ee5599", "#dd4488", "#cc3377",
        "#aa2266", "#881155", "#660044", "#550033", "#440022", "#330011"
    ],
}

# Rainbow colors cycle through these bases
RAINBOW_BASES = ["#ff0000", "#ff8800", "#ffff00", "#00ff00", "#00ffff", "#0088ff", "#8800ff", "#ff00ff"]

def generate_fade_colors(base_hex, steps=11):
    """Generate fading colors from white to dark version of base"""
    r = int(base_hex[1:3], 16)
    g = int(base_hex[3:5], 16)
    b = int(base_hex[5:7], 16)
    
    colors = ["#ffffff"]
    for i in range(1, steps):
        factor = 1 - (i / steps)
        nr = int(r * factor)
        ng = int(g * factor)
        nb = int(b * factor)
        colors.append(f"#{nr:02x}{ng:02x}{nb:02x}")
    return colors

# Matrix characters
MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*+-=<>?!"

class MatrixRain:
    def __init__(self):
        self.root = tk.Tk()
        self.drop_speed, self.refresh_rate, self.spawn_chance = get_speed_settings()
        self.min_length, self.max_length = get_length_settings()
        self.setup()
        
    def setup(self):
        self.root.attributes('-fullscreen', True, '-topmost', True)
        self.root.configure(bg='black')
        hide_taskbar()
        
        self.root.bind("<Any-KeyPress>", lambda e: "break")
        self.root.bind("<Button-1>", lambda e: "break")
        
        def force_focus():
            self.root.focus_force()
            self.root.lift()
            self.root.after(50, force_focus)
        force_focus()
        
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        
        self.char_width = 18
        self.num_columns = self.width // self.char_width
        
        self.drops = []
        self.rainbow_index = 0
        
    def get_colors_for_drop(self):
        """Get fade colors based on color mode"""
        if COLOR_MODE == "rainbow":
            # Each drop gets next rainbow color
            base = RAINBOW_BASES[self.rainbow_index % len(RAINBOW_BASES)]
            self.rainbow_index += 1
            return generate_fade_colors(base)
        elif COLOR_MODE == "multi":
            # Random color for each drop
            base = random.choice(RAINBOW_BASES)
            return generate_fade_colors(base)
        else:
            return COLOR_PALETTES.get(COLOR_MODE, COLOR_PALETTES["green"])
        
    def spawn_drop(self):
        col = random.randint(0, self.num_columns - 1)
        x = col * self.char_width + self.char_width // 2
        speed = self.drop_speed + random.uniform(-1, 1)
        
        self.drops.append({
            'x': x,
            'y': random.randint(-200, 0),
            'trail': [],
            'speed': max(1, speed),
            'length': random.randint(self.min_length, self.max_length),
            'colors': self.get_colors_for_drop()
        })
        
    def update(self):
        if random.random() < self.spawn_chance:
            self.spawn_drop()
            
        drops_to_remove = []
        
        for drop in self.drops:
            drop['y'] += drop['speed']
            
            if drop['y'] > 0 and drop['y'] < self.height + 50:
                char = random.choice(MATRIX_CHARS)
                item = self.canvas.create_text(
                    drop['x'], drop['y'],
                    text=char,
                    fill=drop['colors'][0],
                    font=('Consolas', 14, 'bold')
                )
                drop['trail'].insert(0, item)
            
            # Update colors for trail
            for i, item in enumerate(drop['trail']):
                if i < len(drop['colors']):
                    self.canvas.itemconfig(item, fill=drop['colors'][i])
                    if random.random() < 0.05:
                        self.canvas.itemconfig(item, text=random.choice(MATRIX_CHARS))
                else:
                    self.canvas.delete(item)
                    
            while len(drop['trail']) > drop['length']:
                old_item = drop['trail'].pop()
                self.canvas.delete(old_item)
                
            if drop['y'] > self.height + 300 and len(drop['trail']) == 0:
                drops_to_remove.append(drop)
            elif drop['y'] > self.height + 50:
                if drop['trail']:
                    old_item = drop['trail'].pop()
                    self.canvas.delete(old_item)
                if len(drop['trail']) == 0:
                    drops_to_remove.append(drop)
                    
        for drop in drops_to_remove:
            for item in drop['trail']:
                self.canvas.delete(item)
            if drop in self.drops:
                self.drops.remove(drop)
            
        self.root.after(self.refresh_rate, self.update)
        
    def run(self):
        self.update()
        self.root.mainloop()

try:
    rain = MatrixRain()
    rain.run()
finally:
    show_taskbar()