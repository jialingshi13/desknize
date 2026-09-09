"""python -m desktop_organizer"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from desktop_organizer.ui import main as ui_main
    except ModuleNotFoundError as exc:
        if "tkinter" in str(exc):
            sys.stderr.write(
                "启动失败：未找到 tkinter。\n"
                "Windows 请使用 python.org 官方安装包；"
                "Linux 请安装 python3-tk（例如：sudo apt install python3-tk）。\n"
            )
            raise SystemExit(1) from exc
        raise
    ui_main()


if __name__ == "__main__":
    main()
