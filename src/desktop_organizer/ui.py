"""竖向、平面化窗口：整理、刷新、撤销、检索。"""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from desktop_organizer.app_shortcut import ensure_app_shortcut
from desktop_organizer.arrange import arrange_desktop_icons
from desktop_organizer.mover import execute, load_undo_log, undo_last
from desktop_organizer.planner import (
    PlanItem,
    build_plan,
    discover_desktop,
    list_folders,
    list_shortcuts,
    summarize,
)
from desktop_organizer.searcher import SearchHit, search_files

BG = "#111111"
CARD = "#1A1B16"
ACCENT = "#D5FF40"
MUTED = "#C0C2B8"
WHITE = "#FFFFFF"
INK = "#111111"
DANGER = "#FF6B6B"
LINE = "#2A2B24"


def _pick_font_family(root: tk.Tk) -> str:
    available = {name.lower(): name for name in tkfont.families(root)}
    for name in ("Poppins", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei"):
        if name.lower() in available:
            return available[name.lower()]
    return "Segoe UI"


def _dark_titlebar(window: tk.Misc) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), 4)
    except Exception:
        return


class BigButton(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command,
        *,
        accent: bool = False,
        family: str,
    ) -> None:
        self._command = command
        bg = ACCENT if accent else CARD
        fg = INK if accent else WHITE
        super().__init__(master, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._hover = "#E4FF6A" if accent else "#24251E"
        self._label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            font=(family, 18 if accent else 16, "bold"),
            cursor="hand2",
        )
        self._label.pack(expand=True, fill="both")
        for widget in (self, self._label):
            widget.bind("<Button-1>", lambda _e: self._command())
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event: tk.Event) -> None:
        self.configure(bg=self._hover)
        self._label.configure(bg=self._hover)

    def _on_leave(self, _event: tk.Event) -> None:
        self.configure(bg=self._bg)
        self._label.configure(bg=self._bg)


class OrganizerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("桌面整理")
        self.configure(bg=BG)
        self.geometry("420x740")
        self.minsize(380, 640)
        self.maxsize(520, 980)

        self.family = _pick_font_family(self)
        self._apply_theme()
        _dark_titlebar(self)

        self.desktop = discover_desktop()
        self.plan: list[PlanItem] = []
        self.shortcuts: list[Path] = []
        self.folders: list[Path] = []
        self._hits: list[SearchHit] = []

        self._build()
        self.after(200, self._first_run_shortcut)
        self.refresh_plan()

    def _font(self, size: int, weight: str = "normal") -> tuple[str, int, str]:
        return (self.family, size, weight)

    def _apply_theme(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=WHITE, font=self._font(10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=WHITE, font=self._font(10))
        style.configure(
            "TEntry",
            fieldbackground=CARD,
            foreground=WHITE,
            insertcolor=WHITE,
            bordercolor=LINE,
            lightcolor=LINE,
            darkcolor=LINE,
            padding=8,
        )
        style.map("TEntry", bordercolor=[("focus", ACCENT)])
        style.configure(
            "Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=WHITE,
            bordercolor=CARD,
            font=self._font(10),
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=BG,
            foreground=MUTED,
            font=self._font(9),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", INK)],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=CARD,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
        )

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=5)
        self.rowconfigure(3, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 2))
        tk.Label(
            header,
            text="桌面整理",
            bg=BG,
            fg=ACCENT,
            font=self._font(22, "bold"),
        ).pack(anchor="w")
        self.stats_var = tk.StringVar()
        tk.Label(
            header,
            textvariable=self.stats_var,
            bg=BG,
            fg=MUTED,
            font=self._font(10),
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        self.status_var = tk.StringVar()
        tk.Label(
            self,
            textvariable=self.status_var,
            bg=BG,
            fg=WHITE,
            font=self._font(10),
            wraplength=360,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(2, 6))

        buttons = tk.Frame(self, bg=BG)
        buttons.grid(row=2, column=0, sticky="nsew", padx=22, pady=(2, 6))
        buttons.columnconfigure(0, weight=1)
        buttons.rowconfigure(0, weight=3)
        buttons.rowconfigure(1, weight=2)
        buttons.rowconfigure(2, weight=2)
        BigButton(
            buttons,
            "开始整理",
            self.confirm_organize,
            accent=True,
            family=self.family,
        ).grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        BigButton(buttons, "刷新", self.refresh_plan, family=self.family).grid(
            row=1, column=0, sticky="nsew", pady=(0, 8)
        )
        BigButton(buttons, "撤销", self.undo, family=self.family).grid(row=2, column=0, sticky="nsew")

        search = tk.Frame(self, bg=BG)
        search.grid(row=3, column=0, sticky="ew", padx=22, pady=(2, 4))
        search.columnconfigure(0, weight=1)

        tk.Label(
            search,
            text="检索",
            bg=BG,
            fg=MUTED,
            font=self._font(10, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        row = tk.Frame(search, bg=BG)
        row.grid(row=1, column=0, sticky="ew", pady=(6, 6))
        row.columnconfigure(0, weight=1)
        self.name_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.name_var).grid(row=0, column=0, sticky="ew")
        search_btn = tk.Label(
            row,
            text="搜索",
            bg=ACCENT,
            fg=INK,
            font=self._font(10, "bold"),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        search_btn.grid(row=0, column=1, padx=(8, 0))
        search_btn.bind("<Button-1>", lambda _e: self.run_search())
        self.bind("<Return>", lambda _e: self.run_search())

        self.tree = ttk.Treeview(search, columns=("name",), show="tree", height=3)
        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("name", width=320)
        self.tree.bind("<Double-1>", lambda _e: self.open_selected_hit())

        self.search_status = tk.StringVar(value="按文件名搜索整个桌面")
        tk.Label(
            search,
            textvariable=self.search_status,
            bg=BG,
            fg=MUTED,
            font=self._font(9),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(4, 0))

        self.fail_var = tk.StringVar()
        tk.Label(
            self,
            textvariable=self.fail_var,
            bg=BG,
            fg=DANGER,
            font=self._font(9),
            wraplength=360,
            justify="left",
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 14))

    def _first_run_shortcut(self) -> None:
        created = ensure_app_shortcut(self.desktop)
        if created is not None and created.is_file():
            self.status_var.set("已在桌面创建快捷方式。")
            self.refresh_plan()

    def refresh_plan(self) -> None:
        self.desktop = discover_desktop()
        self.fail_var.set("")
        try:
            self.plan = build_plan(self.desktop)
            self.shortcuts = list_shortcuts(self.desktop)
            self.folders = list_folders(self.desktop)
        except OSError as exc:
            self.plan = []
            self.shortcuts = []
            self.folders = []
            self.status_var.set(f"无法读取桌面：{exc}")
            return

        files, _categories = summarize(self.plan)
        self.stats_var.set(
            f"{files} 个文件 · {len(self.shortcuts)} 个快捷方式 · {len(self.folders)} 个文件夹"
        )
        if load_undo_log() is None:
            self.status_var.set("文件按类型收纳；快捷方式在前，文件夹随后。")
        else:
            self.status_var.set("可以继续整理，或撤销上次操作。")

    def confirm_organize(self) -> None:
        items = list(self.plan)
        if not items and not self.shortcuts and not self.folders:
            self.status_var.set("桌面没有可整理的内容。")
            return
        moved = 0
        failed = []
        if items:
            result = execute(items)
            moved = len(result.moved)
            failed = result.failed
        self.update_idletasks()
        arranged = arrange_desktop_icons(list_shortcuts(self.desktop), list_folders(self.desktop))
        if failed:
            lines = "；".join(f"{item.src.name}（{item.message}）" for item in failed)
            self.fail_var.set(f"{len(failed)} 项失败：{lines}")
        else:
            self.fail_var.set("")
        parts = []
        if moved:
            parts.append(f"已整理 {moved} 个文件")
        if arranged:
            parts.append("已排列图标")
        if parts:
            self.status_var.set("，".join(parts) + "。")
        elif failed:
            self.status_var.set("整理失败。")
        self.refresh_plan()

    def undo(self) -> None:
        if load_undo_log() is None:
            self.status_var.set("没有可撤销的记录。")
            return
        result = undo_last()
        if result.failed and not result.restored:
            self.fail_var.set(result.failed[0].message)
            self.status_var.set("撤销失败。")
            return
        restored = len(result.restored)
        if result.failed:
            lines = "；".join(f"{item.src.name}（{item.message}）" for item in result.failed)
            self.fail_var.set(f"部分撤销失败：{lines}")
        else:
            self.fail_var.set("")
        arrange_desktop_icons(list_shortcuts(self.desktop), list_folders(self.desktop))
        self.status_var.set(f"已撤销 {restored} 个文件。")
        self.refresh_plan()

    def run_search(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._hits = []
        self.tree.grid_remove()
        try:
            hits = search_files(self.desktop, name_query=self.name_var.get())
        except ValueError as exc:
            self.search_status.set(str(exc))
            return
        self._hits = hits[:80]
        for hit in self._hits:
            self.tree.insert("", "end", values=(hit.path.name,))
        if self._hits:
            self.tree.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        extra = "（仅显示前 80 条）" if len(hits) > 80 else ""
        self.search_status.set(f"找到 {len(hits)} 个文件{extra}。双击打开。")

    def _selected_hit(self) -> SearchHit | None:
        selected = self.tree.selection()
        if not selected:
            return None
        index = self.tree.index(selected[0])
        if 0 <= index < len(self._hits):
            return self._hits[index]
        return None

    def open_selected_hit(self) -> None:
        hit = self._selected_hit()
        if hit is None:
            self.search_status.set("请先选中一个结果。")
            return
        try:
            os.startfile(hit.path)  # type: ignore[attr-defined]
        except AttributeError:
            subprocess.run(["xdg-open", str(hit.path)], check=False)


def main() -> None:
    app = OrganizerApp()
    app.mainloop()
