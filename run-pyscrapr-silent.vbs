' PyScrapr silent launcher - runs backend + frontend without visible terminals.
'
' Trade-off: no console output is visible. If backend or frontend crashes
' silently, you won't see why. For debugging, use run-pyscrapr.bat instead.
'
' This script:
'   1. Detects Laragon Python 3.10 (or fallback)
'   2. Spawns backend (run.py) hidden
'   3. Spawns frontend (npm run dev) hidden
'   4. Polls /api/health until ready (max 30s)
'   5. Opens default browser to http://localhost:5173

Option Explicit
Dim sh, fso, root, backendDir, frontendDir, py
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

root = fso.GetParentFolderName(WScript.ScriptFullName)
backendDir = root & "\backend"
frontendDir = root & "\frontend"

' Locate Python (Laragon path first, system fallback)
py = "C:\laragon\bin\python\python-3.10\python.exe"
If Not fso.FileExists(py) Then
    py = "python"
End If

' Spawn backend hidden (window mode 0 = hidden, no taskbar icon)
sh.CurrentDirectory = backendDir
sh.Run "cmd /c """"" & py & """" -u run.py""", 0, False

' Spawn frontend hidden
sh.CurrentDirectory = frontendDir
sh.Run "cmd /c npm run dev", 0, False

' Restore cwd
sh.CurrentDirectory = root

' Wait for backend health (max 30s)
Dim i, http, ready
ready = False
For i = 1 To 30
    WScript.Sleep 1000
    On Error Resume Next
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.SetTimeouts 1000, 1000, 1000, 1000
    http.Open "GET", "http://127.0.0.1:8000/api/health", False
    http.Send
    If Err.Number = 0 And http.Status = 200 Then
        ready = True
        Exit For
    End If
    On Error Goto 0
Next

' Open default browser (window mode 1 = normal visible window)
sh.Run "http://localhost:5173", 1, False
