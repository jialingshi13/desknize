"""执行整理计划：安全移动、冲突改名、撤销上次操作。"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from desktop_organizer.planner import PlanItem, path_key, unique_path

LOG_VERSION = 1


def default_undo_log_path() -> Path:
    return Path.home() / ".desktop_organizer" / "last_undo.json"


@dataclass
class MoveFailure:
    src: Path
    message: str


@dataclass
class MoveResult:
    moved: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[MoveFailure] = field(default_factory=list)
    created_dirs: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.moved) and not self.failed


@dataclass
class UndoResult:
    restored: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[MoveFailure] = field(default_factory=list)
    removed_dirs: list[Path] = field(default_factory=list)


def execute(
    items: list[PlanItem],
    log_path: Path | None = None,
) -> MoveResult:
    """按计划移动文件。部分成功时仍写入可撤销日志。"""
    result = MoveResult()
    reserved: set[str] = set()
    created_seen: set[str] = set()

    for item in items:
        dest = item.dest
        if dest.exists() or path_key(dest) in reserved:
            dest = unique_path(dest, reserved)

        if not item.src.exists():
            result.failed.append(MoveFailure(item.src, "源文件已不存在"))
            continue
        if dest.exists():
            result.failed.append(MoveFailure(item.src, f"目标已存在：{dest}"))
            continue
        if item.src.is_dir():
            try:
                dest_res = dest.resolve()
                src_res = item.src.resolve()
                if dest_res == src_res or dest_res.is_relative_to(src_res):
                    result.failed.append(MoveFailure(item.src, "不能把文件夹移进自身"))
                    continue
            except OSError as exc:
                result.failed.append(MoveFailure(item.src, str(exc)))
                continue

        try:
            created = mkdir_parents(dest.parent)
            shutil.move(str(item.src), str(dest))
        except OSError as exc:
            result.failed.append(MoveFailure(item.src, str(exc)))
            continue

        reserved.add(path_key(dest))
        result.moved.append((item.src, dest))
        for directory in created:
            key = path_key(directory)
            if key not in created_seen:
                created_seen.add(key)
                result.created_dirs.append(directory)

    if result.moved:
        save_undo_log(
            log_path or default_undo_log_path(),
            moved=result.moved,
            created_dirs=result.created_dirs,
        )
    return result


def mkdir_parents(directory: Path) -> list[Path]:
    created: list[Path] = []
    if directory.exists():
        return created
    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for path in reversed(missing):
        path.mkdir(exist_ok=True)
        created.append(path)
    return created


def save_undo_log(
    log_path: Path,
    moved: list[tuple[Path, Path]],
    created_dirs: list[Path],
) -> None:
    payload = {
        "version": LOG_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "moves": [{"src": str(src), "dest": str(dest)} for src, dest in moved],
        "created_dirs": [str(path) for path in created_dirs],
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_undo_log(log_path: Path | None = None) -> dict | None:
    path = log_path or default_undo_log_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("moves"):
        return None
    return data


def undo_last(log_path: Path | None = None) -> UndoResult:
    """把上次整理过的文件移回原处，并尝试删除当时新建的空文件夹。"""
    path = log_path or default_undo_log_path()
    data = load_undo_log(path)
    result = UndoResult()
    if data is None:
        result.failed.append(MoveFailure(path, "没有可撤销的整理记录"))
        return result

    reserved: set[str] = set()
    moves = list(data.get("moves") or [])
    for record in reversed(moves):
        src = Path(record["src"])
        dest = Path(record["dest"])
        if not dest.exists():
            result.failed.append(MoveFailure(dest, "整理后的项目已不在目标位置"))
            continue
        restore_to = src
        if restore_to.exists() or path_key(restore_to) in reserved:
            restore_to = unique_path(src, reserved)
        reserved.add(path_key(restore_to))
        try:
            restore_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dest), str(restore_to))
        except OSError as exc:
            result.failed.append(MoveFailure(dest, str(exc)))
            continue
        result.restored.append((dest, restore_to))

    for directory in reversed(list(data.get("created_dirs") or [])):
        dir_path = Path(directory)
        try:
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                result.removed_dirs.append(dir_path)
        except OSError:
            continue

    if result.restored and not result.failed:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    elif result.restored:
        remaining = [
            record
            for record in moves
            if Path(record["dest"]).exists()
        ]
        save_undo_log(
            path,
            moved=[(Path(r["src"]), Path(r["dest"])) for r in remaining],
            created_dirs=[Path(p) for p in data.get("created_dirs") or []],
        )
        if not remaining:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    return result
