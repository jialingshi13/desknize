"""One-click: install PyInstaller and build desktop_organizer.exe."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "desktop_organizer.spec"
DIST = ROOT / "dist"
EXE_NAME = "desktop_organizer.exe"


def find_python() -> list[str]:
    candidates = [
        [sys.executable],
        ["python"],
        ["py", "-3"],
    ]
    for cmd in candidates:
        try:
            proc = subprocess.run(
                [*cmd, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            continue
        if proc.returncode == 0:
            return cmd
    return []


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def pause() -> None:
    if sys.stdin and sys.stdin.isatty():
        input("Press Enter to close...")


def main() -> None:
    os.chdir(ROOT)
    py = find_python()
    if not py:
        print("Python 3.10+ not found. Install from https://www.python.org/downloads/")
        print('Check "Add python.exe to PATH".')
        raise SystemExit(1)

    print("Using:", " ".join(py), flush=True)
    print("Installing PyInstaller ...", flush=True)
    run([*py, "-m", "pip", "install", "-U", "pip", "pyinstaller"])

    sys.path.insert(0, str(ROOT / "src"))
    from desktop_organizer.brush_icon import write_ico

    ico = ROOT / "packaging" / "app.ico"
    write_ico(ico)
    print("Wrote icon:", ico, flush=True)

    for folder in (ROOT / "build", DIST):
        if folder.exists():
            shutil.rmtree(folder)

    print("Building exe ...", flush=True)
    run([*py, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC)])

    exe = DIST / EXE_NAME
    if not exe.is_file():
        print("Build finished but exe was not found:", exe)
        raise SystemExit(1)

    local_copy = ROOT / "桌面整理.exe"
    shutil.copy2(exe, local_copy)

    print()
    print("OK")
    print(" ", exe)
    print(" ", local_copy)
    print("Double-click either file to run. Python is not required.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if int(exc.code or 1) != 0:
            pause()
        raise
    except Exception as exc:
        print("Build failed:", exc)
        pause()
        raise SystemExit(1) from exc
