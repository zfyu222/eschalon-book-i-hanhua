"""Eschalon Book I Chinese launcher for the isolated DRM-free runtime."""
import csv
import ctypes
import os
import shutil
import struct
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# In the project workspace, launch the isolated test copy.  A PyInstaller
# release is placed directly in the player's game directory, so resolve the
# original game executable beside the frozen launcher instead.
_runtime_override = os.environ.get("ESCHALON_RUNTIME")
RUNTIME = (
    Path(_runtime_override).resolve()
    if _runtime_override
    else (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else ROOT / "Eschalon_CN"
    )
)
EXE = RUNTIME / "eschalon_book_1.exe"
LAUNCH_EXE = EXE
ORIGINAL_CSV = ROOT / "translated_strings.csv"
TRANSLATED_CSV = ROOT / "translated_strings_translated.csv"
FONT_FILES = [
    ROOT / "fonts" / "cn_OldTymeBG.ttf",
    ROOT / "fonts" / "cn_Fantasy.ttf",
    ROOT / "fonts" / "cn_DS_Celtic_1.ttf",
]
FONT_CODE_VAS = [0x490724, 0x490741, 0x49075E]

CREATE_SUSPENDED = 0x00000004
MEM_COMMIT, MEM_RESERVE = 0x1000, 0x2000
PAGE_READWRITE, PAGE_EXECUTE_READWRITE = 0x04, 0x40
INFINITE = 0xFFFFFFFF


class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE), ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                               wintypes.DWORD, wintypes.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = wintypes.BOOL
k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                 wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
k32.VirtualProtectEx.restype = wintypes.BOOL


def win_error(operation):
    raise OSError(f"{operation}: {ctypes.WinError(ctypes.get_last_error())}")


def read_memory(process, address, size):
    buffer = ctypes.create_string_buffer(size)
    done = ctypes.c_size_t()
    if not k32.ReadProcessMemory(process, ctypes.c_void_p(address), buffer, size, ctypes.byref(done)):
        win_error(f"ReadProcessMemory(0x{address:08X})")
    return buffer.raw[:done.value]


def write_memory(process, address, data, executable=False):
    old = wintypes.DWORD()
    changed = False
    if executable:
        if not k32.VirtualProtectEx(process, ctypes.c_void_p(address), len(data),
                                    PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            win_error(f"VirtualProtectEx(0x{address:08X})")
        changed = True
    try:
        source = (ctypes.c_char * len(data)).from_buffer_copy(data)
        done = ctypes.c_size_t()
        if not k32.WriteProcessMemory(process, ctypes.c_void_p(address), source, len(data), ctypes.byref(done)):
            win_error(f"WriteProcessMemory(0x{address:08X})")
        if done.value != len(data):
            raise RuntimeError(f"short write at 0x{address:08X}: {done.value}/{len(data)}")
        if read_memory(process, address, len(data)) != data:
            raise RuntimeError(f"read-back mismatch at 0x{address:08X}")
    finally:
        if changed:
            ignored = wintypes.DWORD()
            k32.VirtualProtectEx(process, ctypes.c_void_p(address), len(data), old.value, ctypes.byref(ignored))
    if executable:
        k32.FlushInstructionCache(process, ctypes.c_void_p(address), len(data))


def load_mapping():
    with ORIGINAL_CSV.open("r", encoding="utf-8-sig", newline="") as stream:
        original = [row[0].strip() for row in list(csv.reader(stream))[1:] if row]
    with TRANSLATED_CSV.open("r", encoding="utf-8-sig", newline="") as stream:
        translated = [row[0].strip() for row in list(csv.reader(stream))[1:] if row]
    return {source: target for source, target in zip(original, translated)
            if source and target and source != target}


def launch_suspended():
    si = STARTUPINFO(cb=ctypes.sizeof(STARTUPINFO)); pi = PROCESS_INFORMATION()
    command = ctypes.create_unicode_buffer(f'"{LAUNCH_EXE}"')
    if not k32.CreateProcessW(None, command, None, None, False, CREATE_SUSPENDED,
                              None, str(RUNTIME), ctypes.byref(si), ctypes.byref(pi)):
        win_error("CreateProcessW")
    return pi


def ensure_steam_identity():
    """Make direct suspended startup behave like the proven dev runtime."""
    app_id = "25600"
    app_id_file = RUNTIME / "steam_appid.txt"
    if not app_id_file.exists() or app_id_file.read_text(
            encoding="ascii", errors="ignore").strip() != app_id:
        app_id_file.write_text(app_id + "\n", encoding="ascii")
    os.environ["SteamAppId"] = app_id
    os.environ["SteamGameId"] = app_id
    return app_id_file


def prepare_injectable_executable():
    """Copy the user's EXE outside Program Files for display-hook injection.

    Some Windows/Steam installations deny Frida's remote allocation after the
    executable starts inside Program Files.  The copied executable is still the
    player's own file and runs with the real game directory as its working
    directory, so all data, music, and saves remain there.  Steam's DRM stub
    also needs the app identity when the image path is outside the library;
    otherwise it stops at "Application load error 5:0000065434".
    """
    global LAUNCH_EXE
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable")
    runtime_dir = Path(local_app_data) / "EschalonBookChineseRuntime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    copied_exe = runtime_dir / EXE.name
    shutil.copy2(EXE, copied_exe)
    os.environ["SteamAppId"] = "25600"
    os.environ["SteamGameId"] = "25600"
    LAUNCH_EXE = copied_exe
    return copied_exe


def cleanup_injectable_executable(copied_exe):
    global LAUNCH_EXE
    LAUNCH_EXE = EXE
    if copied_exe is None:
        return
    try:
        copied_exe.unlink(missing_ok=True)
        copied_exe.parent.rmdir()
    except OSError:
        # A crash or security scanner may briefly retain the file. It contains
        # only a byte-for-byte copy of the user's own executable and is safely
        # overwritten on the next launch.
        pass


def patch_fonts(process):
    allocations = []
    for path, code_va in zip(FONT_FILES, FONT_CODE_VAS):
        data = path.read_bytes()
        address = k32.VirtualAllocEx(process, None, len(data), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not address:
            win_error("VirtualAllocEx(font)")
        write_memory(process, address, data)
        end = address + len(data)
        for offset, value in ((1, end), (6, address), (12, address), (17, end)):
            write_memory(process, code_va + offset, struct.pack("<I", value), executable=True)
        allocations.append((path.name, address, len(data)))
    return allocations


def patch_items(process, mapping):
    address = 0x54159C
    block = read_memory(process, address, 50000)
    end = block.find(b"\0")
    text = block[:end].decode("utf-8")
    output, count = [], 0
    for line in text.split("\r\n"):
        row = next(csv.reader([line])) if line else []
        if len(row) >= 2 and row[1] in mapping and row[1] != "DESCRIPTION":
            row[1] = mapping[row[1]]; count += 1
            from io import StringIO
            holder = StringIO(); csv.writer(holder, lineterminator="").writerow(row)
            line = holder.getvalue()
        output.append(line)
    encoded = "\r\n".join(output).encode("utf-8")
    if len(encoded) > end:
        raise RuntimeError(f"translated item table overflow: {len(encoded)} > {end}")
    write_memory(process, address, encoded + b"\0" * (end - len(encoded) + 1))
    return count


def patch_books(process, mapping):
    address = 0x552770
    block = read_memory(process, address, 50000); end = block.find(b"\0")
    text = block[:end].decode("utf-8"); count = 0
    for source in sorted(mapping, key=len, reverse=True):
        if len(source) >= 10 and source in text:
            text = text.replace(source, mapping[source]); count += 1
    encoded = text.encode("utf-8")
    if len(encoded) > end:
        raise RuntimeError(f"translated book table overflow: {len(encoded)} > {end}")
    write_memory(process, address, encoded + b"\0" * (end - len(encoded) + 1))
    return count


def patch_short_strings(process, mapping):
    address, limit, count, overflow = 0x560000, 0x590000, 0, 0
    while address < limit:
        block = read_memory(process, address, min(2048, limit - address))
        end = block.find(b"\0")
        if end < 0:
            address += len(block); continue
        raw = block[:end]
        if len(raw) >= 5:
            source = raw.decode("utf-8", errors="ignore")
            if source in mapping:
                target = mapping[source].encode("utf-8")
                if len(target) <= len(raw):
                    write_memory(process, address, target + b"\0" * (len(raw) - len(target) + 1))
                    count += 1
                else:
                    overflow += 1
        address += end + 1
    return count, overflow


def main():
    missing = [str(path) for path in [EXE, ORIGINAL_CSV, TRANSLATED_CSV, *FONT_FILES] if not path.exists()]
    if missing:
        print("Missing required files:\n" + "\n".join(missing), file=sys.stderr)
        return 2
    mapping = load_mapping()
    print(f"Loaded {len(mapping)} translations")
    pi = launch_suspended()
    print(f"Game PID: {pi.dwProcessId}")
    try:
        fonts = patch_fonts(pi.hProcess)
        for name, address, size in fonts:
            print(f"Font {name}: 0x{address:08X}, {size:,} bytes")
        print(f"Items translated: {patch_items(pi.hProcess, mapping)}")
        print(f"Books translated: {patch_books(pi.hProcess, mapping)}")
        direct, overflow = patch_short_strings(pi.hProcess, mapping)
        print(f"Short strings translated: {direct}; overflow deferred: {overflow}")
        k32.ResumeThread(pi.hThread)
        print("Chinese runtime started. Close the game to exit this launcher.")
        k32.WaitForSingleObject(pi.hProcess, INFINITE)
    except Exception:
        k32.TerminateProcess(pi.hProcess, 1)
        raise
    finally:
        k32.CloseHandle(pi.hThread); k32.CloseHandle(pi.hProcess)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
