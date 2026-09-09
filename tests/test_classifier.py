from pathlib import Path

from desktop_organizer.classifier import OTHER_CATEGORY, classify, is_shortcut


def test_classify_known_extensions() -> None:
    assert classify(Path("vacation.jpg")) == "图片"
    assert classify(Path("notes.PDF")) == "文档"
    assert classify(Path("sheet.xlsx")) == "表格"
    assert classify(Path("deck.pptx")) == "演示"
    assert classify(Path("clip.mp4")) == "视频"
    assert classify(Path("song.mp3")) == "音乐"
    assert classify(Path("bundle.zip")) == "压缩包"
    assert classify(Path("setup.msi")) == "安装包"
    assert classify(Path("app.py")) == "代码"
    assert classify(Path("site.url")) == "快捷方式"
    assert is_shortcut(Path("app.lnk")) is True
    assert is_shortcut(Path("photo.jpg")) is False


def test_classify_unknown_and_empty() -> None:
    assert classify(Path("readme.xyz")) == OTHER_CATEGORY
    assert classify(Path("LICENSE")) == OTHER_CATEGORY
