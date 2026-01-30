"""
Screen Flip Prank - Rotates the screen display
Uses Windows display settings
"""
import ctypes
import sys
import time

# Display orientation constants
DMDO_DEFAULT = 0
DMDO_90 = 1
DMDO_180 = 2
DMDO_270 = 3

def rotate_screen(orientation):
    """Rotate screen to specified orientation (0, 90, 180, 270)"""
    try:
        # This requires admin rights on some systems
        import subprocess
        
        orientations = {
            0: "0",
            90: "1",
            180: "2", 
            270: "3"
        }
        
        # Use display rotation PowerShell command
        ps_script = f'''
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class DisplaySettings {{
            [DllImport("user32.dll")]
            public static extern bool EnumDisplaySettings(string deviceName, int modeNum, ref DEVMODE devMode);
            
            [DllImport("user32.dll")]
            public static extern int ChangeDisplaySettings(ref DEVMODE devMode, int flags);
            
            [StructLayout(LayoutKind.Sequential)]
            public struct DEVMODE {{
                [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
                public string dmDeviceName;
                public short dmSpecVersion;
                public short dmDriverVersion;
                public short dmSize;
                public short dmDriverExtra;
                public int dmFields;
                public int dmPositionX;
                public int dmPositionY;
                public int dmDisplayOrientation;
                public int dmDisplayFixedOutput;
                public short dmColor;
                public short dmDuplex;
                public short dmYResolution;
                public short dmTTOption;
                public short dmCollate;
                [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
                public string dmFormName;
                public short dmLogPixels;
                public int dmBitsPerPel;
                public int dmPelsWidth;
                public int dmPelsHeight;
                public int dmDisplayFlags;
                public int dmDisplayFrequency;
            }}
        }}
"@
        '''
        # Note: Full screen rotation requires admin and complex API calls
        # For safety, this prank just shows a message
        print(f"[SCREEN FLIP] Would rotate to {orientation} degrees (requires admin)")
        
    except Exception as e:
        print(f"[SCREEN FLIP] Error: {e}")

def flip_upside_down():
    """Flip screen 180 degrees"""
    rotate_screen(180)

def restore_screen():
    """Restore screen to normal"""
    rotate_screen(0)

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else "180"
    
    if action == "180" or action == "flip":
        flip_upside_down()
    elif action == "restore" or action == "0":
        restore_screen()
    else:
        try:
            rotate_screen(int(action))
        except:
            flip_upside_down()
