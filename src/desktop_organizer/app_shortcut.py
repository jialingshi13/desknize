"""首次运行时在桌面创建带刷子图标的程序快捷方式，并刷新图标。"""

from __future__ import annotations

import sys
from pathlib import Path

from desktop_organizer.brush_icon import write_ico
from desktop_organizer.planner import discover_desktop

APP_DIR = Path.home() / ".desktop_organizer"
SHORTCUT_NAME = "桌面整理.lnk"
MARKER = APP_DIR / "shortcut_created"


def _target() -> tuple[str, str, str]:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return str(exe), "", str(exe.parent)
    run_py = Path(__file__).resolve().parents[2] / "run.py"
    if run_py.is_file():
        return sys.executable, f'"{run_py}"', str(run_py.parent)
    return sys.executable, "-m desktop_organizer", str(Path.cwd())


def _icon_path(target: str) -> str:
    if getattr(sys, "frozen", False) and Path(target).is_file():
        return target
    return str(write_ico(APP_DIR / "brush.ico"))


def ensure_app_shortcut(desktop: Path | None = None) -> Path | None:
    """写入刷子图标；没有快捷方式则创建，已有则更新图标。"""
    if sys.platform != "win32":
        return None
    try:
        desktop = desktop or discover_desktop()
        shortcut = desktop / SHORTCUT_NAME
        existed = shortcut.is_file()
        target, args, workdir = _target()
        icon = _icon_path(target)
        if not _write_shortcut(shortcut, target, args, workdir, icon):
            return None
        MARKER.parent.mkdir(parents=True, exist_ok=True)
        MARKER.write_text("1", encoding="utf-8")
        _notify_shell(shortcut)
        return None if existed else shortcut
    except Exception:
        return None


def _write_shortcut(path: Path, target: str, args: str, workdir: str, icon: str) -> bool:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize.restype = ctypes.c_long
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.IIDFromString.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    ole32.IIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p]
    ole32.CoInitialize(None)

    clsid = GUID()
    iid_link = GUID()
    iid_file = GUID()
    ole32.IIDFromString("{00021401-0000-0000-C000-000000000046}", ctypes.byref(clsid))
    ole32.IIDFromString("{000214F9-0000-0000-C000-000000000046}", ctypes.byref(iid_link))
    ole32.IIDFromString("{0000010b-0000-0000-C000-000000000046}", ctypes.byref(iid_file))

    link = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid),
        None,
        23,
        ctypes.byref(iid_link),
        ctypes.byref(link),
    )
    if hr != 0 or not link.value:
        return False

    vtbl = ctypes.cast(link, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

    def com(index: int, restype, argtypes):
        proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        return proto(vtbl[index])

    try:
        com(20, ctypes.c_long, [ctypes.c_wchar_p])(link, target)
        com(11, ctypes.c_long, [ctypes.c_wchar_p])(link, args)
        com(9, ctypes.c_long, [ctypes.c_wchar_p])(link, workdir)
        com(15, ctypes.c_long, [ctypes.c_int])(link, 1)
        com(7, ctypes.c_long, [ctypes.c_wchar_p])(link, "桌面整理")
        com(17, ctypes.c_long, [ctypes.c_wchar_p, ctypes.c_int])(link, icon, 0)

        persist = ctypes.c_void_p()
        hr = com(0, ctypes.c_long, [ctypes.c_void_p, ctypes.c_void_p])(
            link, ctypes.byref(iid_file), ctypes.byref(persist)
        )
        if hr != 0 or not persist.value:
            return False
        pvtbl = ctypes.cast(persist, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

        def pcom(index: int, restype, argtypes):
            proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
            return proto(pvtbl[index])

        hr = pcom(6, ctypes.c_long, [ctypes.c_wchar_p, wintypes.BOOL])(persist, str(path), True)
        pcom(2, ctypes.c_ulong, [])(persist)
        return hr == 0 and path.is_file()
    finally:
        com(2, ctypes.c_ulong, [])(link)


def _notify_shell(shortcut: Path) -> None:
    try:
        import ctypes

        SHCNE_UPDATEITEM = 0x00002000
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_PATHW = 0x0005
        SHCNF_FLUSH = 0x1000
        SHCNF_IDLIST = 0x0000
        path = ctypes.c_wchar_p(str(shortcut))
        ctypes.windll.shell32.SHChangeNotify(
            SHCNE_UPDATEITEM, SHCNF_PATHW | SHCNF_FLUSH, path, None
        )
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        return
