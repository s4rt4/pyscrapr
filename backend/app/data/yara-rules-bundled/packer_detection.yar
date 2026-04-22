rule Packer_UPX
{
    meta:
        description = "UPX-packed executable"
        severity = "medium"
    strings:
        $upx1 = "UPX0"
        $upx2 = "UPX1"
        $upx3 = "UPX!"
    condition:
        any of them
}

rule Packer_ASPack
{
    meta:
        description = "ASPack-packed executable"
        severity = "medium"
    strings:
        $s1 = ".aspack"
        $s2 = ".adata"
    condition:
        any of them
}

rule Packer_Themida
{
    meta:
        description = "Themida / WinLicense packer"
        severity = "medium"
    strings:
        $t1 = "Themida"
        $t2 = ".themida"
        $w1 = "WinLicense"
    condition:
        any of them
}

rule Packer_MPRESS
{
    meta:
        description = "MPRESS packer"
        severity = "medium"
    strings:
        $m1 = ".MPRESS1"
        $m2 = ".MPRESS2"
    condition:
        any of them
}
