"""在桌面范围内按名称、后缀和修改时间检索文件。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from desktop_organizer.classifier import classify, file_suffix
from desktop_organizer.planner import SKIP_NAMES, own_executable_names

SKIP_DIR_NAMES = frozenset({".git", "__pycache__", ".desktop_organizer"})


@dataclass(frozen=True)
class SearchHit:
    path: Path
    suffix: str
    category: str
    modified: datetime | None

    @property
    def modified_label(self) -> str:
        if self.modified is None:
            return "未知"
        return self.modified.strftime("%Y-%m-%d %H:%M")


def parse_day(text: str) -> date | None:
    raw = text.strip()
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _modified_at(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None


def _suffixes(raw: str) -> set[str] | None:
    text = raw.strip().lower().replace("，", ",")
    if not text or text in {"全部", "*", "all"}:
        return None
    items = {part.strip().lstrip(".") for part in text.split(",") if part.strip()}
    return items or None


def search_files(
    root: Path,
    name_query: str = "",
    suffix_text: str = "",
    after_text: str = "",
    before_text: str = "",
) -> list[SearchHit]:
    """递归检索 root 下的文件。日期为空表示不限制；起止日期按本地日历日闭区间。"""
    if not root.is_dir():
        return []

    try:
        after = parse_day(after_text) if after_text.strip() else None
        before = parse_day(before_text) if before_text.strip() else None
    except ValueError as exc:
        raise ValueError("日期请使用 YYYY-MM-DD，例如 2026-09-01") from exc
    wanted = _suffixes(suffix_text)
    needle = name_query.strip().lower()
    skip_names = SKIP_NAMES | {name.lower() for name in own_executable_names()}

    hits: list[SearchHit] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if path.name.lower() in skip_names:
            continue
        if any(part.lower() in SKIP_DIR_NAMES for part in path.parts):
            continue
        if needle and needle not in path.name.lower():
            continue
        suffix = file_suffix(path)
        if wanted is not None and suffix not in wanted:
            continue
        modified = _modified_at(path)
        if after is not None:
            if modified is None or modified.date() < after:
                continue
        if before is not None:
            if modified is None or modified.date() > before:
                continue
        hits.append(
            SearchHit(
                path=path,
                suffix=suffix or "（无）",
                category=classify(path),
                modified=modified,
            )
        )

    hits.sort(key=lambda hit: (hit.modified or datetime.min, hit.path.name.lower()), reverse=True)
    return hits
