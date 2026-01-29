import tkinter as tk
import sys
import subprocess

def show_single_error():
    try:
        r = tk.Tk()
        r.title("Error")
        r.attributes('-topmost', True)
        r.attributes('-disabled', True)
        r.after(100, lambda: r.focus_force())
        r.grab_set()
        
        # Random position
        import random
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        r.geometry("400x150+"+str(x)+"+"+str(y))
        
        r.configure(bg="black")
        
        tk.Label(r, text="SYSTEM FAILURE", fg="white", bg="black", font=("Segoe UI", 14, "bold")).pack(pady=8)
        tk.Label(r, text="A fatal exception has occurred.", fg="white", bg="black").pack()
        tk.Button(r, text="OK", command=r.destroy, bg="white", fg="black").pack(pady=10)
        r.mainloop()
    except:
        pass

if __name__ == "__main__":
    # Usage: python fake_error.py count:5
    if len(sys.argv) > 1 and sys.argv[1].startswith("count:"):
        try:
            count = int(sys.argv[1].split(":")[1])
            # Spawn detached processes
            DETACHED_PROCESS = 0x00000008
            for _ in range(count):
                subprocess.Popen([sys.executable, __file__, "display"], creationflags=DETACHED_PROCESS)
        except:
            pass
    else:
        # Display mode (prevents recursion)
        show_single_error()