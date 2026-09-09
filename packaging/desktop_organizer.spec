# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from desktop_organizer.brush_icon import write_ico

ICO = ROOT / "packaging" / "app.ico"
write_ico(ICO)

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT), str(ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "desktop_organizer",
        "desktop_organizer.__main__",
        "desktop_organizer.classifier",
        "desktop_organizer.planner",
        "desktop_organizer.mover",
        "desktop_organizer.ui",
        "desktop_organizer.searcher",
        "desktop_organizer.arrange",
        "desktop_organizer.app_shortcut",
        "desktop_organizer.brush_icon",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="desktop_organizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICO),
)
