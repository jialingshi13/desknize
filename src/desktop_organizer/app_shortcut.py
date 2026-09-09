"""首次运行时在桌面创建带刷子图标的程序快捷方式，并刷新图标。"""

from __future__ import annotations

import subprocess
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


def ensure_app_shortcut(desktop: Path | None = None) -> Path | None:
    """写入刷子图标；没有快捷方式则创建，已有则更新图标。"""
    if sys.platform != "win32":
        return None
    desktop = desktop or discover_desktop()
    shortcut = desktop / SHORTCUT_NAME
    existed = shortcut.is_file()
    icon = write_ico(APP_DIR / "brush.ico")
    target, args, workdir = _target()
    argument_literal = "" if not args else f"'{_ps(args)}'"
    ps = f"""
$ErrorActionPreference = 'Stop'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{_ps(shortcut)}')
$s.TargetPath = '{_ps(target)}'
$s.Arguments = {argument_literal if argument_literal else "''"}
$s.WorkingDirectory = '{_ps(workdir)}'
$s.WindowStyle = 1
$s.Description = '桌面整理'
$s.IconLocation = '{_ps(icon)},0'
$s.Save()
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not shortcut.is_file():
        return None
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("1", encoding="utf-8")
    _notify_shell()
    return None if existed else shortcut


def _notify_shell() -> None:
    try:
        import ctypes

        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        return


def _ps(value: str | Path) -> str:
    return str(value).replace("'", "''")
