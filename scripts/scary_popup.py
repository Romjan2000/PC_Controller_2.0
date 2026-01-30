"""
PC Controller - Scary Popup Prank
A frightening fullscreen popup with creepy effects.
"""
import tkinter as tk
import random
import sys
import math

class ScaryPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.load_assets()
        self.create_widgets()
        self.start_effects()
        
    def setup_window(self):
        """Make fullscreen black window"""
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        self.root.overrideredirect(True)
        
        # Get screen dimensions
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        
        # Bind escape to close (secret exit)
        self.root.bind('<Escape>', lambda e: self.close())
        self.root.bind('<space>', lambda e: self.close())
        
        # Auto close after 10 seconds
        self.root.after(10000, self.close)
        
    def load_assets(self):
        """Prepare scary elements"""
        self.scary_texts = [
            "I'M WATCHING YOU",
            "I CAN SEE YOU",
            "DON'T LOOK BEHIND YOU",
            "I'M IN YOUR WALLS",
            "YOU CAN'T ESCAPE",
            "I KNOW WHAT YOU DID",
            "I'VE BEEN HERE ALL ALONG",
            "DO YOU FEEL THAT?",
            "BEHIND YOU...",
            "I'M GETTING CLOSER",
        ]
        
        self.glitch_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        
    def create_widgets(self):
        """Create the scary interface"""
        # Main canvas for drawing effects
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_w,
            height=self.screen_h,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Create scary text elements
        self.create_scary_face()
        self.create_glitch_text()
        
    def create_scary_face(self):
        """Create a creepy ASCII face in the center"""
        face = """
              ████████████████              
          ████░░░░░░░░░░░░░░████          
        ██░░░░░░░░░░░░░░░░░░░░░░██        
      ██░░░░░░░░░░░░░░░░░░░░░░░░░░██      
    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██    
    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██    
  ██░░░░████████░░░░░░░░████████░░░░░░██  
  ██░░░░██    ██░░░░░░░░██    ██░░░░░░██  
  ██░░░░████████░░░░░░░░████████░░░░░░██  
  ██░░░░░░░░░░░░░░████░░░░░░░░░░░░░░░░██  
  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██  
    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░██    
    ██░░██░░░░░░░░░░░░░░░░░░░░░░██░░██    
      ██░░████████████████████░░██      
        ██░░░░░░░░░░░░░░░░░░░░██        
          ████░░░░░░░░░░░░████          
              ████████████              
"""
        
        self.face_label = tk.Label(
            self.canvas,
            text=face,
            font=('Consolas', 8),
            fg='#ff0000',
            bg='black',
            justify='center'
        )
        self.canvas.create_window(
            self.screen_w // 2,
            self.screen_h // 2 - 50,
            window=self.face_label
        )
        
        # Scary text below face
        self.scary_label = tk.Label(
            self.canvas,
            text="I'M WATCHING YOU",
            font=('Impact', 48, 'bold'),
            fg='#ff0000',
            bg='black'
        )
        self.canvas.create_window(
            self.screen_w // 2,
            self.screen_h // 2 + 200,
            window=self.scary_label
        )
        
    def create_glitch_text(self):
        """Create random glitch text around the screen"""
        self.glitch_labels = []
        
        for _ in range(15):
            x = random.randint(50, self.screen_w - 200)
            y = random.randint(50, self.screen_h - 100)
            
            text = random.choice(self.scary_texts)
            size = random.randint(12, 24)
            
            label = tk.Label(
                self.canvas,
                text=text,
                font=('Consolas', size, 'bold'),
                fg=random.choice(['#ff0000', '#880000', '#ff3333', '#cc0000']),
                bg='black'
            )
            self.canvas.create_window(x, y, window=label)
            self.glitch_labels.append(label)
            
    def start_effects(self):
        """Start all scary effects"""
        self.flash_count = 0
        self.flicker()
        self.glitch_text()
        self.pulsate_face()
        self.shake_screen()
        
    def flicker(self):
        """Random screen flicker effect"""
        if random.random() < 0.3:
            # Flash effect
            self.canvas.configure(bg='#330000')
            self.root.after(50, lambda: self.canvas.configure(bg='black'))
            
        self.root.after(random.randint(100, 500), self.flicker)
        
    def glitch_text(self):
        """Make scary text glitch"""
        # Glitch the main text
        if random.random() < 0.4:
            new_text = random.choice(self.scary_texts)
            # Add glitch characters occasionally
            if random.random() < 0.3:
                glitch = ''.join(random.choice(self.glitch_chars) for _ in range(3))
                new_text = glitch + new_text + glitch
            self.scary_label.config(text=new_text)
            
        # Glitch random labels
        for label in self.glitch_labels:
            if random.random() < 0.2:
                new_text = random.choice(self.scary_texts)
                label.config(text=new_text)
                
        self.root.after(random.randint(100, 400), self.glitch_text)
        
    def pulsate_face(self):
        """Make the face pulsate red"""
        colors = ['#ff0000', '#cc0000', '#990000', '#660000', '#990000', '#cc0000']
        color_idx = int(self.flash_count % len(colors))
        self.face_label.config(fg=colors[color_idx])
        self.flash_count += 1
        self.root.after(150, self.pulsate_face)
        
    def shake_screen(self):
        """Subtle screen shake effect"""
        if random.random() < 0.2:
            dx = random.randint(-5, 5)
            dy = random.randint(-5, 5)
            current_geo = self.root.geometry()
            self.root.geometry(f'+{dx}+{dy}')
            self.root.after(50, lambda: self.root.geometry('+0+0'))
            
        self.root.after(200, self.shake_screen)
        
    def close(self):
        """Close the popup"""
        self.root.destroy()
        
    def run(self):
        """Start the popup"""
        self.root.mainloop()

def run_scary_popup():
    """Entry point"""
    try:
        popup = ScaryPopup()
        popup.run()
    except Exception as e:
        print(f"Scary popup error: {e}")

if __name__ == "__main__":
    run_scary_popup()
