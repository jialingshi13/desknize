"""扫描桌面根目录，生成按类型与年/月分层的整理计划。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from desktop_organizer.classifier import classify, is_shortcut

UNKNOWN_DATE = "未知日期"

SKIP_NAMES = frozenset(
    {
        "desktop.ini",
        "thumbs.db",
        ".ds_store",
        "iconcache.db",
    }
)

OWN_EXE_NAMES = frozenset({"desktop_organizer.exe", "desktoporganizer.exe", "桌面整理.exe"})


@dataclass(frozen=True)
class PlanItem:
    src: Path
    dest: Path
    category: str
    year: str
    month: str

    @property
    def date_label(self) -> str:
        if self.year == UNKNOWN_DATE:
            return UNKNOWN_DATE
        return f"{self.year}/{self.month}"

    @property
    def relative_dest(self) -> str:
        try:
            return self.dest.relative_to(self.src.parent).as_posix()
        except ValueError:
            return self.dest.as_posix()


def discover_desktop(home: Path | None = None) -> Path:
    """定位当前用户桌面目录；找不到时回退到 ~/Desktop。"""
    home = Path.home() if home is None else home
    real_home = home.resolve() == Path.home().resolve()
    candidates: list[Path] = []

    if real_home:
        windows = _windows_desktop()
        if windows is not None:
            candidates.append(windows)

    xdg = _xdg_from_config(home)
    if xdg is not None:
        candidates.append(xdg)
    elif real_home:
        env = os.environ.get("XDG_DESKTOP_DIR")
        if env:
            candidates.append(Path(env).expanduser())

    candidates.extend([home / "Desktop", home / "桌面"])

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_dir():
            return candidate

    return home / "Desktop"


def own_executable_names() -> set[str]:
    names = {name.lower() for name in OWN_EXE_NAMES}
    if getattr(sys, "frozen", False):
        names.add(Path(sys.executable).name.lower())
    return names


def should_skip(path: Path, extra_skip_names: set[str] | None = None) -> bool:
    name = path.name.lower()
    if name in SKIP_NAMES:
        return True
    if name.startswith("."):
        return True
    if path.is_dir():
        return True
    if not path.is_file():
        return True
    skip = own_executable_names()
    if extra_skip_names:
        skip |= {item.lower() for item in extra_skip_names}
    return name in skip


def file_year_month(path: Path) -> tuple[str, str]:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return UNKNOWN_DATE, ""
    return f"{mtime.year:04d}", f"{mtime.month:02d}"


def intended_dest(desktop: Path, src: Path, category: str, year: str, month: str) -> Path:
    if year == UNKNOWN_DATE:
        return desktop / category / UNKNOWN_DATE / src.name
    return desktop / category / year / month / src.name


def path_key(path: Path) -> str:
    normalized = os.path.normpath(str(path))
    if sys.platform == "win32":
        return os.path.normcase(normalized)
    return normalized


def unique_path(dest: Path, reserved: set[str]) -> Path:
    """若目标已存在或已被本轮计划占用，则追加 (2)、(3) 后缀。"""
    if path_key(dest) not in reserved and not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    n = 2
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if path_key(candidate) not in reserved and not candidate.exists():
            return candidate
        n += 1


def list_shortcuts(desktop: Path, extra_skip_names: set[str] | None = None) -> list[Path]:
    """桌面根目录中的快捷方式，不移动，只用于排列。"""
    if not desktop.is_dir():
        return []
    try:
        entries = list(desktop.iterdir())
    except OSError:
        return []
    shortcuts: list[Path] = []
    for entry in entries:
        if should_skip(entry, extra_skip_names):
            continue
        if is_shortcut(entry):
            shortcuts.append(entry)
    shortcuts.sort(key=lambda path: path.name.lower())
    return shortcuts


def list_folders(desktop: Path) -> list[Path]:
    """桌面根目录中的文件夹，不移动，整理后排在快捷方式后面。"""
    if not desktop.is_dir():
        return []
    try:
        entries = list(desktop.iterdir())
    except OSError:
        return []
    folders: list[Path] = []
    for entry in entries:
        name = entry.name.lower()
        if name in SKIP_NAMES or name.startswith("."):
            continue
        if entry.is_dir():
            folders.append(entry)
    folders.sort(key=lambda path: path.name.lower())
    return folders


def build_plan(desktop: Path, extra_skip_names: set[str] | None = None) -> list[PlanItem]:
    """只扫描桌面根目录文件。快捷方式和文件夹不进入计划，只在桌面上分组排列。"""
    if not desktop.is_dir():
        return []

    raw: list[tuple[Path, str, str, str]] = []
    try:
        entries = list(desktop.iterdir())
    except OSError:
        return []

    for entry in entries:
        if should_skip(entry, extra_skip_names):
            continue
        if is_shortcut(entry):
            continue
        if not entry.is_file():
            continue
        category = classify(entry)
        year, month = file_year_month(entry)
        raw.append((entry, category, year, month))

    raw.sort(key=lambda item: (item[1], item[2], item[3], item[0].name.lower()))

    reserved: set[str] = set()
    items: list[PlanItem] = []
    for src, category, year, month in raw:
        dest = unique_path(intended_dest(desktop, src, category, year, month), reserved)
        reserved.add(path_key(dest))
        items.append(
            PlanItem(src=src, dest=dest, category=category, year=year, month=month)
        )
    return items


def summarize(items: list[PlanItem]) -> tuple[int, int]:
    categories = {item.category for item in items}
    return len(items), len(categories)


def _windows_desktop() -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buffer)
        path = Path(buffer.value)
        return path if str(path) else None
    except Exception:
        return None


def _xdg_from_config(home: Path) -> Path | None:
    config = home / ".config" / "user-dirs.dirs"
    if not config.is_file():
        return None
    try:
        text = config.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("XDG_DESKTOP_DIR="):
            continue
        raw = stripped.split("=", 1)[1].strip().strip('"').strip("'")
        raw = raw.replace("$HOME", str(home))
        return Path(raw)
    return None
