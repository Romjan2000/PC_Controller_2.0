"""
PC Controller - Matrix ASCII Art Display
Converts an image to Matrix-style ASCII art and displays it in a fullscreen terminal window.
"""
import sys
import os
from PIL import Image
import tkinter as tk

# ASCII characters from darkest to lightest
ASCII_CHARS = " .,:;+*?%S#@"
ASCII_CHARS_REVERSED = ASCII_CHARS[::-1]

def image_to_ascii(image_path, width=120):
    """Convert image to ASCII art string"""
    try:
        img = Image.open(image_path)
    except Exception as e:
        return f"Error loading image: {e}"
    
    # Calculate height maintaining aspect ratio (terminal chars are ~2x tall as wide)
    aspect_ratio = img.height / img.width
    height = int(width * aspect_ratio * 0.5)
    
    # Resize image
    img = img.resize((width, height))
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Convert pixels to ASCII
    pixels = list(img.getdata())
    ascii_art = ""
    
    for i, pixel in enumerate(pixels):
        # Map pixel value (0-255) to ASCII character
        char_index = pixel * (len(ASCII_CHARS_REVERSED) - 1) // 255
        ascii_art += ASCII_CHARS_REVERSED[char_index]
        
        if (i + 1) % width == 0:
            ascii_art += "\n"
    
    return ascii_art

class MatrixDisplay:
    """Fullscreen Matrix-style ASCII art display"""
    
    def __init__(self, ascii_art):
        self.ascii_art = ascii_art
        self.root = tk.Tk()
        self.setup()
        
    def setup(self):
        # Fullscreen black window
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        
        # No local close bindings - only controllable via PC Controller
        
        # Get screen size
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Calculate font size to fit
        lines = self.ascii_art.split('\n')
        num_lines = len(lines)
        max_line_len = max(len(line) for line in lines) if lines else 1
        
        # Calculate optimal font size
        font_h = max(6, min(14, screen_h // (num_lines + 2)))
        font_w = max(4, min(10, screen_w // (max_line_len + 2)))
        font_size = min(font_h, font_w)
        
        # Text widget for ASCII art
        text = tk.Text(
            self.root,
            font=('Consolas', font_size),
            fg='#00ff00',  # Matrix green
            bg='black',
            relief='flat',
            highlightthickness=0,
            cursor='none'
        )
        text.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Insert ASCII art
        text.insert('1.0', self.ascii_art)
        text.config(state='disabled')
        
        # Center the content
        text.tag_configure('center', justify='center')
        text.tag_add('center', '1.0', 'end')
        
    def run(self):
        self.root.mainloop()

def display_matrix_image(image_path, width=None):
    """Main function to convert and display image as Matrix ASCII art"""
    
    # Auto-detect width based on screen size and image size
    if width is None:
        try:
            # Get screen dimensions
            root = tk.Tk()
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            root.destroy()
            
            # Check image dimensions
            img = Image.open(image_path)
            img_w, img_h = img.size
            img.close()
            
            # For large/wide images (like screenshots), use smaller width
            if img_w > 2000 or img_h > 1500:
                # Large image - reduce width to fit better
                width = min(160, max(100, screen_w // 12))
            else:
                # Normal image
                width = min(180, max(80, screen_w // 8))
                
        except Exception as e:
            print(f"Warning: {e}")
            width = 120
    
    print(f"Converting image to ASCII art (width={width})...")
    ascii_art = image_to_ascii(image_path, width)
    
    if ascii_art.startswith("Error"):
        print(ascii_art)
        return False
    
    print("Displaying Matrix ASCII art...")
    display = MatrixDisplay(ascii_art)
    display.run()
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python matrix_image.py <image_path> [width]")
        print("Example: python matrix_image.py photo.jpg 120")
        sys.exit(1)
    
    image_path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        sys.exit(1)
    
    display_matrix_image(image_path, width)
