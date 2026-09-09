#!/usr/bin/env python3
"""不安装包时也可直接运行：python run.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from desktop_organizer.__main__ import main

if __name__ == "__main__":
    main()
