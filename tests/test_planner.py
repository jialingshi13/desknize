from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from desktop_organizer.planner import (
    UNKNOWN_DATE,
    build_plan,
    discover_desktop,
    intended_dest,
    should_skip,
    unique_path,
)


def test_discover_desktop_prefers_existing_desktop(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    assert discover_desktop(tmp_path) == desktop


def test_discover_desktop_supports_chinese_name(tmp_path: Path) -> None:
    desktop = tmp_path / "桌面"
    desktop.mkdir()
    assert discover_desktop(tmp_path) == desktop


def test_build_plan_categorizes_by_type_and_mtime(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    photo = desktop / "vacation.jpg"
    photo.write_bytes(b"img")
    stamp = datetime(2026, 9, 8, 12, 0, 0).timestamp()
    os.utime(photo, (stamp, stamp))

    nested = desktop / "already" / "inside.png"
    nested.parent.mkdir()
    nested.write_bytes(b"png")

    items = build_plan(desktop)
    assert len(items) == 1
    item = items[0]
    assert item.category == "图片"
    assert item.year == "2026"
    assert item.month == "09"
    assert item.dest == desktop / "图片" / "2026" / "09" / "vacation.jpg"


def test_build_plan_skips_folders_hidden_and_system_files(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "folder").mkdir()
    (desktop / "图片").mkdir()
    (desktop / "desktop.ini").write_text("x")
    (desktop / ".hidden.txt").write_text("x")
    (desktop / "desktop_organizer.exe").write_bytes(b"mz")
    keep = desktop / "keep.pdf"
    keep.write_bytes(b"pdf")
    (desktop / "chrome.lnk").write_bytes(b"lnk")
    (desktop / "mail.url").write_text("URL")

    items = build_plan(desktop)
    assert [item.src.name for item in items] == ["keep.pdf"]


def test_list_folders_sorted_and_includes_managed(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "Work").mkdir()
    (desktop / "archive").mkdir()
    (desktop / "图片").mkdir()
    (desktop / ".hidden_dir").mkdir()
    (desktop / "photo.jpg").write_bytes(b"img")

    from desktop_organizer.planner import list_folders

    names = [path.name for path in list_folders(desktop)]
    assert names == ["archive", "Work", "图片"]


def test_list_shortcuts_sorted_and_not_moved(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "b.lnk").write_bytes(b"b")
    (desktop / "A.lnk").write_bytes(b"a")
    (desktop / "photo.jpg").write_bytes(b"img")

    from desktop_organizer.planner import list_shortcuts

    names = [path.name for path in list_shortcuts(desktop)]
    assert names == ["A.lnk", "b.lnk"]
    assert [item.src.name for item in build_plan(desktop)] == ["photo.jpg"]


def test_should_skip_folders_and_system_files(tmp_path: Path) -> None:
    folder = tmp_path / "dir"
    folder.mkdir()
    assert should_skip(folder) is True
    ini = tmp_path / "desktop.ini"
    ini.write_text("x")
    assert should_skip(ini) is True
    hidden = tmp_path / ".hidden"
    hidden.write_text("x")
    assert should_skip(hidden) is True


def test_unique_path_adds_numeric_suffix(tmp_path: Path) -> None:
    dest = tmp_path / "photo.jpg"
    dest.write_bytes(b"a")
    (tmp_path / "photo (2).jpg").write_bytes(b"b")
    result = unique_path(tmp_path / "photo.jpg", reserved=set())
    assert result.name == "photo (3).jpg"


def test_intended_dest_unknown_date(tmp_path: Path) -> None:
    src = tmp_path / "odd.bin"
    dest = intended_dest(tmp_path, src, "其他", UNKNOWN_DATE, "")
    assert dest == tmp_path / "其他" / UNKNOWN_DATE / "odd.bin"


def test_discover_desktop_reads_user_dirs(tmp_path: Path) -> None:
    desktop = tmp_path / "MyDesk"
    desktop.mkdir()
    config = tmp_path / ".config"
    config.mkdir()
    (config / "user-dirs.dirs").write_text(
        'XDG_DESKTOP_DIR="$HOME/MyDesk"\n',
        encoding="utf-8",
    )
    assert discover_desktop(tmp_path) == desktop
