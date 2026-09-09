from __future__ import annotations

from datetime import datetime
from pathlib import Path

from desktop_organizer.searcher import search_files


def test_search_filters_by_suffix_and_date(tmp_path: Path) -> None:
    photo = tmp_path / "a.jpg"
    note = tmp_path / "notes.pdf"
    other = tmp_path / "keep.txt"
    nested = tmp_path / "图片" / "2026" / "09"
    nested.mkdir(parents=True)
    nested_photo = nested / "b.png"
    photo.write_bytes(b"jpg")
    note.write_bytes(b"pdf")
    other.write_bytes(b"txt")
    nested_photo.write_bytes(b"png")

    old = datetime(2024, 1, 1, 12, 0, 0).timestamp()
    new = datetime(2026, 9, 8, 12, 0, 0).timestamp()
    import os

    os.utime(photo, (new, new))
    os.utime(note, (old, old))
    os.utime(other, (new, new))
    os.utime(nested_photo, (new, new))

    jpg_hits = search_files(tmp_path, suffix_text="jpg,png")
    assert {hit.path.name for hit in jpg_hits} == {"a.jpg", "b.png"}

    dated = search_files(tmp_path, after_text="2026-01-01", before_text="2026-12-31")
    assert {hit.path.name for hit in dated} == {"a.jpg", "keep.txt", "b.png"}

    named = search_files(tmp_path, name_query="keep")
    assert [hit.path.name for hit in named] == ["keep.txt"]
