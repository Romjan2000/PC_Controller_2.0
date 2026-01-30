"""
Crazy Mouse Prank - Makes the mouse move randomly and erratically
"""
import pyautogui
import random
import time
import sys

pyautogui.FAILSAFE = False

def crazy_mouse():
    speed = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    
    delays = {
        "LAGGY": 0.3,
        "NORMAL": 0.1,
        "FAST": 0.05,
        "INSANE": 0.02
    }
    delay = delays.get(speed, 0.1)
    
    print(f"[CRAZY MOUSE] Starting with speed: {speed}")
    
    screen_width, screen_height = pyautogui.size()
    
    while True:
        # Random movement patterns
        pattern = random.choice(['shake', 'jump', 'spiral', 'edges'])
        
        if pattern == 'shake':
            # Shake around current position
            for _ in range(random.randint(10, 30)):
                dx = random.randint(-50, 50)
                dy = random.randint(-50, 50)
                pyautogui.moveRel(dx, dy, duration=0)
                time.sleep(delay)
        
        elif pattern == 'jump':
            # Jump to random position
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            pyautogui.moveTo(x, y, duration=0)
            time.sleep(delay * 3)
        
        elif pattern == 'spiral':
            # Spiral movement
            import math
            cx, cy = pyautogui.position()
            for i in range(50):
                angle = i * 0.3
                radius = i * 2
                x = cx + int(radius * math.cos(angle))
                y = cy + int(radius * math.sin(angle))
                x = max(0, min(screen_width - 1, x))
                y = max(0, min(screen_height - 1, y))
                pyautogui.moveTo(x, y, duration=0)
                time.sleep(delay)
        
        elif pattern == 'edges':
            # Run to screen edges
            edge = random.choice(['top', 'bottom', 'left', 'right'])
            if edge == 'top':
                pyautogui.moveTo(random.randint(0, screen_width), 0)
            elif edge == 'bottom':
                pyautogui.moveTo(random.randint(0, screen_width), screen_height - 1)
            elif edge == 'left':
                pyautogui.moveTo(0, random.randint(0, screen_height))
            else:
                pyautogui.moveTo(screen_width - 1, random.randint(0, screen_height))
            time.sleep(delay * 5)

if __name__ == '__main__':
    crazy_mouse()
