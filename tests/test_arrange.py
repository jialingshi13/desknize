from pathlib import Path

from desktop_organizer.arrange import grid_positions, group_icon_names, stay_order, _match_indices


def test_stay_order_shortcuts_then_folders(tmp_path: Path) -> None:
    shortcuts = [tmp_path / "b.lnk", tmp_path / "A.lnk"]
    folders = [tmp_path / "Work", tmp_path / "archive"]
    names = [path.name for path in stay_order(shortcuts, folders)]
    assert names == ["A.lnk", "b.lnk", "archive", "Work"]


def test_grid_positions_fill_columns() -> None:
    points = grid_positions(5, origin=(0, 0), spacing=(75, 80), rows=3)
    assert points == [
        (0, 0),
        (0, 80),
        (0, 160),
        (75, 0),
        (75, 80),
    ]


def test_match_indices_uses_stem_for_shortcuts() -> None:
    names = ["Chrome", "Work", "Notes"]
    targets = [Path("chrome.lnk"), Path("Work")]
    assert _match_indices(names, targets) == [0, 1]


def test_group_icon_names_shortcuts_then_folders() -> None:
    names = ["回收站", "Work", "Chrome", "图片"]
    shortcuts = [Path("chrome.lnk")]
    folders = [Path("图片"), Path("Work")]
    assert group_icon_names(names, shortcuts, folders) == [2, 1, 3, 0]


def test_match_indices_uses_parsing_path() -> None:
    names = ["Google Chrome", "项目"]
    parsing = [r"C:\Users\a\Desktop\chrome.lnk", r"C:\Users\a\Desktop\项目"]
    targets = [Path(r"C:\Users\a\Desktop\chrome.lnk")]
    assert _match_indices(names, targets, parsing) == [0]
