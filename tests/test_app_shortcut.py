from __future__ import annotations

import sys
from pathlib import Path

import pytest

from desktop_organizer.app_shortcut import _write_shortcut


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcut COM")
def test_write_shortcut_creates_lnk(tmp_path: Path) -> None:
    target = sys.executable
    shortcut = tmp_path / "桌面整理.lnk"
    assert _write_shortcut(shortcut, target, "", str(tmp_path), target) is True
    assert shortcut.is_file()
    assert shortcut.stat().st_size > 0
