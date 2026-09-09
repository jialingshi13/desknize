from pathlib import Path

from desktop_organizer.brush_icon import write_ico


def test_write_brush_ico(tmp_path: Path) -> None:
    icon = write_ico(tmp_path / "brush.ico")
    data = icon.read_bytes()
    assert icon.is_file()
    assert data[:4] == b"\x00\x00\x01\x00"
    assert data[4:6] == b"\x05\x00"
    assert len(data) > 1000
