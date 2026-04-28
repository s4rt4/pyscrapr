' Stop PyScrapr silent launcher.
' Kills python.exe + node.exe processes that match PyScrapr backend/frontend.
' Use this after launching via run-pyscrapr-silent.vbs since there are no
' visible windows to close manually.

Option Explicit
Dim sh, killed
Set sh = CreateObject("WScript.Shell")

' Kill any python.exe whose command line includes 'run.py' (our backend)
sh.Run "cmd /c wmic process where ""name='python.exe' and CommandLine like '%%run.py%%'"" call terminate", 0, True

' Kill any node.exe whose command line includes 'vite' (our frontend dev server)
sh.Run "cmd /c wmic process where ""name='node.exe' and CommandLine like '%%vite%%'"" call terminate", 0, True

' Notify (small message box, auto-dismiss after 2s)
MsgBox "PyScrapr backend dan frontend dihentikan.", vbInformation + vbOKOnly, "PyScrapr"
