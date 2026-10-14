' PC Controller - Completely Silent Background Launcher (No Popups / No Flashing Console)
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Set working directory to this script's directory
strFolder = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strFolder

' Determine Python executable (venv preferred, system fallback)
strPython = "pythonw.exe"
If fso.FileExists(strFolder & "\venv\Scripts\pythonw.exe") Then
    strPython = """" & strFolder & "\venv\Scripts\pythonw.exe"""
End If

' Run completely hidden (0 = SW_HIDE, False = don't block)
WshShell.Run strPython & " Controller.pyw", 0, False
