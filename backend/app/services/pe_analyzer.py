"""PE header / imports / sections analysis."""
from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("pyscrapr.threat.pe")

_SUSPICIOUS_IMPORTS = {
    "VirtualAlloc", "VirtualAllocEx", "VirtualProtect", "VirtualProtectEx",
    "WriteProcessMemory", "ReadProcessMemory",
    "CreateRemoteThread", "CreateRemoteThreadEx", "NtCreateThreadEx",
    "LoadLibraryA", "LoadLibraryW", "LoadLibraryExA", "LoadLibraryExW",
    "GetProcAddress", "GetModuleHandleA", "GetModuleHandleW",
    "IsDebuggerPresent", "CheckRemoteDebuggerPresent", "NtQueryInformationProcess",
    "ShellExecuteA", "ShellExecuteW", "ShellExecuteExA", "ShellExecuteExW",
    "WinExec", "CreateProcessA", "CreateProcessW",
    "URLDownloadToFileA", "URLDownloadToFileW",
    "InternetOpenA", "InternetOpenUrlA", "HttpSendRequestA",
    "OpenProcess", "NtOpenProcess",
    "SetWindowsHookExA", "SetWindowsHookExW",
    "CryptEncrypt", "CryptDecrypt",
    "AdjustTokenPrivileges",
}


def _subsystem_name(sub: int) -> str:
    return {
        1: "NATIVE", 2: "WINDOWS_GUI", 3: "WINDOWS_CUI",
        5: "OS2_CUI", 7: "POSIX_CUI", 9: "WINDOWS_CE_GUI",
        10: "EFI_APPLICATION", 11: "EFI_BOOT_SERVICE_DRIVER",
        12: "EFI_RUNTIME_DRIVER", 13: "EFI_ROM", 14: "XBOX",
    }.get(int(sub), f"UNKNOWN_{sub}")


def _machine_name(m: int) -> str:
    return {
        0x014c: "I386", 0x8664: "AMD64", 0x01c0: "ARM",
        0xaa64: "ARM64", 0x0200: "IA64",
    }.get(int(m), f"UNKNOWN_0x{m:04x}")


def _section_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    from collections import Counter
    import math
    counts = Counter(data)
    total = len(data)
    e = 0.0
    for c in counts.values():
        p = c / total
        e -= p * math.log2(p)
    return round(e, 3)


def analyze_pe(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "machine": None,
        "subsystem": None,
        "is_dll": False,
        "is_exe": False,
        "sections": [],
        "imports": [],
        "suspicious_imports": [],
        "is_packed": False,
        "timestamp": None,
        "compile_timestamp_suspicious": False,
        "error": None,
        "available": False,
    }
    try:
        import pefile  # type: ignore
    except Exception as e:
        out["error"] = f"pefile tidak tersedia: {e}"
        return out

    try:
        pe = pefile.PE(str(path), fast_load=False)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out

    out["available"] = True

    try:
        fh = pe.FILE_HEADER
        out["machine"] = _machine_name(fh.Machine)
        out["is_dll"] = bool(fh.Characteristics & 0x2000)
        out["is_exe"] = not out["is_dll"]

        ts = int(fh.TimeDateStamp)
        try:
            dt = _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc)
            out["timestamp"] = dt.isoformat()
            now = _dt.datetime.now(tz=_dt.timezone.utc)
            if dt > now or dt.year < 1995:
                out["compile_timestamp_suspicious"] = True
        except Exception:
            pass

        try:
            out["subsystem"] = _subsystem_name(pe.OPTIONAL_HEADER.Subsystem)
        except Exception:
            pass

        # Sections
        high_entropy_count = 0
        for sec in pe.sections:
            try:
                raw = sec.get_data()
                ent = _section_entropy(raw)
            except Exception:
                ent = 0.0
            name = sec.Name.rstrip(b"\x00").decode(errors="ignore")
            sus = ent > 7.2
            if sus:
                high_entropy_count += 1
            out["sections"].append({
                "name": name,
                "size": int(sec.SizeOfRawData),
                "virtual_size": int(sec.Misc_VirtualSize),
                "entropy": ent,
                "suspicious": sus,
            })
        if high_entropy_count >= 1 and len(pe.sections) <= 4:
            out["is_packed"] = True

        # Imports
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            imports_list = []
            sus_set: set[str] = set()
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll = entry.dll.decode(errors="ignore") if entry.dll else ""
                fns = []
                for imp in entry.imports:
                    if imp.name:
                        n = imp.name.decode(errors="ignore")
                        fns.append(n)
                        if n in _SUSPICIOUS_IMPORTS:
                            sus_set.add(n)
                imports_list.append({"dll": dll, "functions": fns[:50]})
            out["imports"] = imports_list[:50]
            out["suspicious_imports"] = sorted(sus_set)

    except Exception as e:
        out["error"] = f"parse error: {e}"
    finally:
        try:
            pe.close()
        except Exception:
            pass

    return out
