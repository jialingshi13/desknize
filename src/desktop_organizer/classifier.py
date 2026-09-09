"""按扩展名把文件归到固定分类。"""

from __future__ import annotations

from pathlib import Path

# 分类名保持稳定：界面、目标文件夹、测试都依赖这些字符串。
OTHER_CATEGORY = "其他"
FOLDER_CATEGORY = "文件夹"

CATEGORY_EXTENSIONS: dict[str, frozenset[str]] = {
    "图片": frozenset(
        {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "heic", "tiff"}
    ),
    "文档": frozenset({"pdf", "doc", "docx", "txt", "md", "rtf", "odt", "epub"}),
    "表格": frozenset({"xls", "xlsx", "csv", "ods"}),
    "演示": frozenset({"ppt", "pptx"}),
    "视频": frozenset({"mp4", "mkv", "avi", "mov", "wmv", "webm"}),
    "音乐": frozenset({"mp3", "wav", "flac", "aac", "m4a", "ogg"}),
    "压缩包": frozenset({"zip", "rar", "7z", "tar", "gz"}),
    "安装包": frozenset({"exe", "msi", "apk", "iso"}),
    "代码": frozenset(
        {"py", "js", "ts", "html", "css", "json", "java", "c", "cpp", "go", "rs"}
    ),
    "快捷方式": frozenset({"lnk", "url"}),
}

MANAGED_OUTPUT_NAMES = frozenset(
    {*CATEGORY_EXTENSIONS.keys(), OTHER_CATEGORY, FOLDER_CATEGORY} - {"快捷方式"}
)

_EXTENSION_TO_CATEGORY: dict[str, str] = {
    ext: category
    for category, extensions in CATEGORY_EXTENSIONS.items()
    for ext in extensions
}


def file_suffix(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def is_shortcut(path: Path) -> bool:
    return file_suffix(path) in CATEGORY_EXTENSIONS["快捷方式"]


def classify(path: Path) -> str:
    """根据扩展名返回分类名；无法识别时返回「其他」。"""
    ext = file_suffix(path)
    if not ext:
        return OTHER_CATEGORY
    return _EXTENSION_TO_CATEGORY.get(ext, OTHER_CATEGORY)
