"""
CD Tray Prank - Opens and closes the CD/DVD drive tray
"""
import ctypes
import time
import sys

def eject_cd():
    """Open the CD tray"""
    ctypes.windll.winmm.mciSendStringW("set cdaudio door open", None, 0, None)
    print("[CD TRAY] Opened")

def close_cd():
    """Close the CD tray"""
    ctypes.windll.winmm.mciSendStringW("set cdaudio door closed", None, 0, None)
    print("[CD TRAY] Closed")

def disco_cd(times=5, delay=1.5):
    """Open and close repeatedly (disco mode!)"""
    for i in range(times):
        eject_cd()
        time.sleep(delay)
        close_cd()
        time.sleep(delay)
    print(f"[CD TRAY] Disco complete ({times} cycles)")

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else "eject"
    
    if action == "eject" or action == "open":
        eject_cd()
    elif action == "close":
        close_cd()
    elif action == "disco":
        times = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        disco_cd(times)
    else:
        eject_cd()
