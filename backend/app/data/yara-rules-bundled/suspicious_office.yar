rule Office_AutoExec_Macro
{
    meta:
        description = "Office document with VBA auto-execution markers"
        severity = "high"
    strings:
        $a1 = "AutoOpen" nocase
        $a2 = "Auto_Open" nocase
        $a3 = "AutoExec" nocase
        $a4 = "AutoClose" nocase
        $a5 = "Document_Open" nocase
        $a6 = "Workbook_Open" nocase
        $shell = "Shell" nocase
        $wsh = "WScript.Shell" nocase
        $ps = "powershell" nocase
    condition:
        any of ($a*) and (any of ($shell, $wsh, $ps))
}

rule Office_DDE_Injection
{
    meta:
        description = "DDE auto-exec pattern in Office docs"
        severity = "high"
    strings:
        $dde1 = "DDEAUTO" nocase
        $dde2 = "DDE " nocase
        $cmd = "cmd.exe" nocase
    condition:
        any of ($dde*) and $cmd
}

rule Office_ActiveX_Suspicious
{
    meta:
        description = "Office doc using ActiveX to load payload"
        severity = "medium"
    strings:
        $ax1 = "ActiveXObject" nocase
        $ax2 = "CreateObject" nocase
        $load = "LoadLibrary" nocase
        $run = "Run(" nocase
    condition:
        any of them
}
