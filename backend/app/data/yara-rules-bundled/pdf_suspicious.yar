rule PDF_With_JavaScript
{
    meta:
        description = "PDF containing embedded JavaScript"
        severity = "medium"
    strings:
        $pdf = "%PDF-"
        $js1 = "/JavaScript"
        $js2 = "/JS"
    condition:
        $pdf at 0 and any of ($js*)
}

rule PDF_OpenAction_Launch
{
    meta:
        description = "PDF OpenAction auto-launch payload"
        severity = "high"
    strings:
        $pdf = "%PDF-"
        $o = "/OpenAction"
        $l = "/Launch"
        $aa = "/AA"
    condition:
        $pdf at 0 and ($o or $l or $aa)
}

rule PDF_Embedded_File
{
    meta:
        description = "PDF carrying embedded file"
        severity = "medium"
    strings:
        $pdf = "%PDF-"
        $emb = "/EmbeddedFile"
        $ef = "/EmbeddedFiles"
    condition:
        $pdf at 0 and ($emb or $ef)
}
