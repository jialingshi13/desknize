from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from desktop_organizer.mover import execute, load_undo_log, undo_last
from desktop_organizer.planner import PlanItem, build_plan


def _dated_file(path: Path, year: int, month: int) -> None:
    path.write_bytes(b"data")
    stamp = datetime(year, month, 1, 10, 0, 0).timestamp()
    os.utime(path, (stamp, stamp))


def test_execute_moves_files_and_undo_restores(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    _dated_file(desktop / "shot.png", 2026, 9)
    _dated_file(desktop / "notes.pdf", 2025, 12)
    log_path = tmp_path / "undo.json"

    items = build_plan(desktop)
    result = execute(items, log_path=log_path)

    assert len(result.moved) == 2
    assert not result.failed
    assert not (desktop / "shot.png").exists()
    assert (desktop / "图片" / "2026" / "09" / "shot.png").is_file()
    assert (desktop / "文档" / "2025" / "12" / "notes.pdf").is_file()
    assert load_undo_log(log_path) is not None

    undone = undo_last(log_path)
    assert len(undone.restored) == 2
    assert not undone.failed
    assert (desktop / "shot.png").is_file()
    assert (desktop / "notes.pdf").is_file()
    assert not (desktop / "图片" / "2026" / "09").exists()
    assert load_undo_log(log_path) is None


def test_execute_renames_when_destination_exists(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    dest_dir = desktop / "图片" / "2026" / "09"
    dest_dir.mkdir(parents=True)
    (dest_dir / "dup.jpg").write_bytes(b"old")
    _dated_file(desktop / "dup.jpg", 2026, 9)
    log_path = tmp_path / "undo.json"

    items = build_plan(desktop)
    assert items[0].dest.name == "dup (2).jpg"
    result = execute(items, log_path=log_path)
    assert len(result.moved) == 1
    assert (dest_dir / "dup.jpg").read_bytes() == b"old"
    assert (dest_dir / "dup (2).jpg").is_file()


def test_execute_skips_missing_source(tmp_path: Path) -> None:
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    missing = desktop / "gone.txt"
    item = PlanItem(
        src=missing,
        dest=desktop / "文档" / "2026" / "01" / "gone.txt",
        category="文档",
        year="2026",
        month="09",
    )
    result = execute([item], log_path=tmp_path / "undo.json")
    assert not result.moved
    assert result.failed[0].src == missing
