"""
Random Sounds Prank - Plays random system sounds or beeps at random intervals
"""
import winsound
import time
import random
import sys

def random_sounds():
    speed = sys.argv[1] if len(sys.argv) > 1 else "NORMAL"
    
    # Delay ranges based on speed
    delays = {
        "LAGGY": (10, 30),
        "NORMAL": (5, 15),
        "FAST": (2, 8),
        "INSANE": (0.5, 3)
    }
    min_delay, max_delay = delays.get(speed, (5, 15))
    
    # System sounds
    sounds = [
        "SystemAsterisk",
        "SystemExclamation", 
        "SystemHand",
        "SystemQuestion",
        "SystemDefault"
    ]
    
    print(f"[RANDOM SOUNDS] Starting with speed: {speed}")
    
    while True:
        # Random choice: system sound or beep
        if random.random() > 0.3:
            # Play system sound
            sound = random.choice(sounds)
            winsound.PlaySound(sound, winsound.SND_ALIAS | winsound.SND_ASYNC)
        else:
            # Play random beep
            freq = random.randint(200, 2000)
            duration = random.randint(50, 500)
            try:
                winsound.Beep(freq, duration)
            except:
                pass
        
        # Random delay
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

if __name__ == '__main__':
    random_sounds()
