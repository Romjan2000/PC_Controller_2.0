"""
PC Controller - Input Blocker Module (VERIFIED WORKING)
Blocks physical mouse and keyboard input using Windows low-level hooks.

KEY FIX: Use NULL (None) as module handle for low-level hooks
SAFETY: Ctrl+Alt+Del is handled by the kernel and CANNOT be blocked!
"""

import ctypes
from ctypes import wintypes, CFUNCTYPE, c_int, byref
import threading
import time
import atexit

# Define types
LRESULT = c_int
HOOKPROC = CFUNCTYPE(LRESULT, c_int, wintypes.WPARAM, wintypes.LPARAM)

# Load DLLs with use_last_error for proper error handling
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Setup function signatures
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

# Constants
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012

# Global state
mouse_blocked = False
keyboard_blocked = False
keyboard_hook = None
mouse_hook = None
hook_thread = None
hook_thread_id = None
hooks_ready = threading.Event()

def _keyboard_callback(nCode, wParam, lParam):
    """Keyboard hook callback - return 1 to block"""
    global keyboard_blocked
    if nCode >= 0 and keyboard_blocked:
        return 1  # Block the input
    return user32.CallNextHookEx(keyboard_hook, nCode, wParam, lParam)

def _mouse_callback(nCode, wParam, lParam):
    """Mouse hook callback - return 1 to block"""
    global mouse_blocked
    if nCode >= 0 and mouse_blocked:
        return 1  # Block the input
    return user32.CallNextHookEx(mouse_hook, nCode, wParam, lParam)

# CRITICAL: Keep references at module level to prevent garbage collection!
_keyboard_hook_proc = HOOKPROC(_keyboard_callback)
_mouse_hook_proc = HOOKPROC(_mouse_callback)

def _hook_thread_func():
    """Thread that installs hooks and runs message loop"""
    global keyboard_hook, mouse_hook, hook_thread_id
    
    hook_thread_id = kernel32.GetCurrentThreadId()
    
    # Install keyboard hook with NULL module handle (KEY FIX!)
    keyboard_hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL,
        _keyboard_hook_proc,
        None,  # NULL module handle - required for low-level hooks
        0
    )
    
    # Install mouse hook with NULL module handle
    mouse_hook = user32.SetWindowsHookExW(
        WH_MOUSE_LL,
        _mouse_hook_proc,
        None,  # NULL module handle - required for low-level hooks
        0
    )
    
    if keyboard_hook and mouse_hook:
        print(f"[INPUT BLOCKER] OK - Hooks installed! KB={keyboard_hook} Mouse={mouse_hook}")
        hooks_ready.set()
    else:
        kb_err = ctypes.get_last_error() if not keyboard_hook else 0
        mouse_err = ctypes.get_last_error() if not mouse_hook else 0
        print(f"[INPUT BLOCKER] FAILED - Hook error! KB={keyboard_hook} (err={kb_err}) Mouse={mouse_hook} (err={mouse_err})")
        hooks_ready.set()  # Set anyway to unblock waiting
        return
    
    # Message loop - REQUIRED for hooks to receive events
    msg = wintypes.MSG()
    while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
        pass  # Just pump messages
    
    # Cleanup when message loop exits
    if keyboard_hook:
        user32.UnhookWindowsHookEx(keyboard_hook)
        keyboard_hook = None
    if mouse_hook:
        user32.UnhookWindowsHookEx(mouse_hook)
        mouse_hook = None
    
    print("[INPUT BLOCKER] Hooks removed")

def _ensure_hooks_running():
    """Start hook thread if not already running"""
    global hook_thread
    
    if hook_thread is not None and hook_thread.is_alive():
        return hooks_ready.is_set()
    
    hooks_ready.clear()
    hook_thread = threading.Thread(target=_hook_thread_func, daemon=True)
    hook_thread.start()
    
    # Wait for hooks to be ready (max 2 seconds)
    return hooks_ready.wait(timeout=2.0)

def block_mouse(block=True):
    """Enable or disable mouse blocking"""
    global mouse_blocked
    
    if block:
        success = _ensure_hooks_running()
        if not success:
            print("[INPUT BLOCKER] Warning: Hooks may not be installed")
    
    mouse_blocked = block
    print(f"[INPUT BLOCKER] Mouse blocked: {mouse_blocked}")
    return mouse_blocked

def block_keyboard(block=True):
    """Enable or disable keyboard blocking"""
    global keyboard_blocked
    
    if block:
        success = _ensure_hooks_running()
        if not success:
            print("[INPUT BLOCKER] Warning: Hooks may not be installed")
    
    keyboard_blocked = block
    print(f"[INPUT BLOCKER] Keyboard blocked: {keyboard_blocked}")
    return keyboard_blocked

def get_status():
    """Get current blocking status"""
    return {
        'mouse_blocked': mouse_blocked,
        'keyboard_blocked': keyboard_blocked,
        'hooks_ready': hooks_ready.is_set()
    }

def unblock_all():
    """Unblock all input (safety function)"""
    global mouse_blocked, keyboard_blocked
    mouse_blocked = False
    keyboard_blocked = False
    print("[INPUT BLOCKER] All input unblocked")

def stop_hooks():
    """Stop the hook thread and cleanup"""
    unblock_all()
    if hook_thread_id:
        user32.PostThreadMessageW(hook_thread_id, WM_QUIT, 0, 0)

# Register cleanup on exit
atexit.register(unblock_all)

# =============================================================================
# TEST
# =============================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  INPUT BLOCKER TEST (VERIFIED WORKING)")
    print("  This will block your mouse and keyboard!")
    print("  Ctrl+Alt+Del will ALWAYS work to escape.")
    print("=" * 60)
    print()
    
    input("Press ENTER to start test...")
    
    print("\nStarting hooks...")
    success = _ensure_hooks_running()
    
    if success and hooks_ready.is_set():
        print("✓ Hooks installed successfully!\n")
    else:
        print("✗ Failed to install hooks!")
        exit(1)
    
    print(">>> Blocking MOUSE in 2 seconds... <<<")
    time.sleep(2)
    block_mouse(True)
    print("MOUSE BLOCKED! Try moving - it won't move!")
    time.sleep(4)
    
    print("\n>>> Also blocking KEYBOARD... <<<")
    block_keyboard(True)
    print("KEYBOARD + MOUSE BLOCKED! Try typing - nothing happens!")
    time.sleep(4)
    
    print("\n>>> Unblocking all... <<<")
    unblock_all()
    print("INPUT RESTORED!\n")
    
    print("Test complete!")
