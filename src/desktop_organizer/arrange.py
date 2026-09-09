"""把桌面快捷方式和文件夹分组对齐到网格，不移动到分类目录。"""

from __future__ import annotations

import sys
from pathlib import Path

from desktop_organizer.planner import path_key

SVSI_POSITIONITEM = 0x00000200
FWF_AUTOARRANGE = 0x00000001
FWF_SNAPTOGRID = 0x00000004
FVO_CUSTOMPOSITION = 0x00000001
FVO_CUSTOMORDERING = 0x00000002
SVGIO_ALLVIEW = 0
SHGDN_NORMAL = 0x0000
SHGDN_FORPARSING = 0x8000


def stay_order(shortcuts: list[Path], folders: list[Path]) -> list[Path]:
    """先快捷方式、再文件夹，各组按名称排序。"""
    return _sorted_paths(shortcuts) + _sorted_paths(folders)


def group_icon_names(
    names: list[str],
    shortcuts: list[Path],
    folders: list[Path],
    parsing_paths: list[str | None] | None = None,
) -> list[int]:
    """返回桌面图标应摆放的顺序：快捷方式、文件夹、其余。"""
    shortcut_idx = _match_indices(names, shortcuts, parsing_paths)
    used = set(shortcut_idx)
    folder_idx = _match_indices(names, folders, parsing_paths, skip=used)
    used.update(folder_idx)
    rest = [i for i in range(len(names)) if i not in used]
    return shortcut_idx + folder_idx + rest


def grid_positions(
    count: int,
    origin: tuple[int, int],
    spacing: tuple[int, int],
    rows: int,
) -> list[tuple[int, int]]:
    """从上到下填满一列，再换到下一列。"""
    if count <= 0:
        return []
    rows = max(1, rows)
    ox, oy = origin
    dx, dy = spacing
    positions: list[tuple[int, int]] = []
    for index in range(count):
        col, row = divmod(index, rows)
        positions.append((ox + col * dx, oy + row * dy))
    return positions


def arrange_shortcuts(shortcuts: list[Path], folders: list[Path] | None = None) -> int:
    """兼容旧调用：只传快捷方式时，文件夹视为空。"""
    return arrange_desktop_icons(shortcuts, folders or [])


def arrange_desktop_icons(shortcuts: list[Path], folders: list[Path]) -> int:
    """Windows 上按「快捷方式 → 文件夹」排列桌面图标；其他系统返回 0。"""
    if sys.platform != "win32":
        return 0
    if not shortcuts and not folders:
        return 0
    try:
        placed = _arrange_via_folderview(shortcuts, folders)
        if placed:
            return placed
    except Exception:
        pass
    try:
        return _arrange_via_listview(shortcuts, folders)
    except Exception:
        return 0


def _sorted_paths(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda path: path.name.casefold())


def _aliases(path: Path) -> set[str]:
    aliases = {path.name.casefold(), path.stem.casefold()}
    try:
        aliases.add(path_key(path))
        aliases.add(str(path).casefold())
    except OSError:
        pass
    return aliases


def _match_indices(
    names: list[str],
    targets: list[Path],
    parsing_paths: list[str | None] | None = None,
    skip: set[int] | None = None,
) -> list[int]:
    unused = [i for i in range(len(names)) if i not in (skip or set())]
    lowered = [name.casefold() for name in names]
    parsed = [(item.casefold() if item else "") for item in (parsing_paths or [None] * len(names))]
    indices: list[int] = []
    for path in _sorted_paths(targets):
        aliases = _aliases(path)
        found = None
        for i in unused:
            if parsed[i] and (parsed[i] in aliases or Path(parsed[i]).name.casefold() in aliases):
                found = i
                break
            if lowered[i] in aliases:
                found = i
                break
        if found is None:
            continue
        unused.remove(found)
        indices.append(found)
    return indices


def _guid(text: str):
    import ctypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    guid = GUID()
    ctypes.oledll.ole32.IIDFromString(text, ctypes.byref(guid))
    return guid


def _vtbl(punk):
    import ctypes

    return ctypes.cast(punk, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents


def _com(punk, index: int, restype, argtypes):
    import ctypes

    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(_vtbl(punk)[index])


def _release(punk) -> None:
    import ctypes

    if not punk:
        return
    try:
        _com(punk, 2, ctypes.c_ulong, [])(punk)
    except Exception:
        return


def _qi(punk, iid: str):
    import ctypes

    out = ctypes.c_void_p()
    guid = _guid(iid)
    hr = _com(punk, 0, ctypes.c_long, [ctypes.c_void_p, ctypes.c_void_p])(
        punk, ctypes.byref(guid), ctypes.byref(out)
    )
    if hr != 0 or not out.value:
        return None
    return out.value


def _folder_view():
    import ctypes
    from ctypes import wintypes

    ole32 = ctypes.oledll.ole32
    ole32.CoInitialize(None)

    clsid = _guid("{9BA05972-F6A8-11CF-A442-00A0C90A8F39}")
    iid_windows = _guid("{85CB6900-4D95-11CF-960C-0080C7F4EE85}")
    windows = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid),
        None,
        23,
        ctypes.byref(iid_windows),
        ctypes.byref(windows),
    )
    if hr != 0 or not windows.value:
        return None

    class VARIANT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("lVal", ctypes.c_int), ("llVal", ctypes.c_longlong)]

        _fields_ = [
            ("vt", ctypes.c_ushort),
            ("wReserved1", ctypes.c_ushort),
            ("wReserved2", ctypes.c_ushort),
            ("wReserved3", ctypes.c_ushort),
            ("n1", _U),
        ]

    loc = VARIANT()
    loc.vt = 3
    loc.n1.lVal = 0
    empty = VARIANT()
    hwnd = ctypes.c_long()
    dispatch = ctypes.c_void_p()
    hr = _com(
        windows.value,
        15,
        ctypes.c_long,
        [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ],
    )(
        windows.value,
        ctypes.byref(loc),
        ctypes.byref(empty),
        8,
        ctypes.byref(hwnd),
        1,
        ctypes.byref(dispatch),
    )
    _release(windows.value)
    if hr != 0 or not dispatch.value:
        return None

    provider = _qi(dispatch.value, "{6D5140C1-7436-11CE-8034-00AA006009FA}")
    _release(dispatch.value)
    if not provider:
        return None

    browser = ctypes.c_void_p()
    sid = _guid("{4C96BE40-915C-11CF-99D3-00AA004AE837}")
    iid_browser = _guid("{000214E2-0000-0000-C000-000000000046}")
    hr = _com(provider, 3, ctypes.c_long, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p])(
        provider, ctypes.byref(sid), ctypes.byref(iid_browser), ctypes.byref(browser)
    )
    _release(provider)
    if hr != 0 or not browser.value:
        return None

    view = ctypes.c_void_p()
    hr = _com(browser.value, 15, ctypes.c_long, [ctypes.c_void_p])(
        browser.value, ctypes.byref(view)
    )
    _release(browser.value)
    if hr != 0 or not view.value:
        return None

    folder_view = _qi(view.value, "{CDE725B0-CCC9-4519-917E-325D72FAB4CE}")
    _release(view.value)
    return folder_view


def _display_name(folder, pidl, flags: int) -> str:
    import ctypes

    class STRRET(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [
                ("pOleStr", ctypes.c_void_p),
                ("uOffset", ctypes.c_uint),
                ("cStr", ctypes.c_char * 260),
            ]

        _fields_ = [("uType", ctypes.c_uint), ("n1", _U)]

    strret = STRRET()
    hr = _com(folder, 11, ctypes.c_long, [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p])(
        folder, pidl, flags, ctypes.byref(strret)
    )
    if hr != 0:
        return ""
    buf = ctypes.create_unicode_buffer(520)
    ctypes.windll.shlwapi.StrRetToBufW(ctypes.byref(strret), pidl, buf, 520)
    return buf.value


def _prepare_custom_layout(folder_view) -> None:
    import ctypes

    options = _qi(folder_view, "{3CC974D2-B302-4D36-AD3E-06D93F695D3F}")
    if options:
        mask = FVO_CUSTOMPOSITION | FVO_CUSTOMORDERING
        _com(options, 3, ctypes.c_long, [ctypes.c_uint, ctypes.c_uint])(options, mask, mask)
        _release(options)

    view2 = _qi(folder_view, "{1AF3A467-214F-4298-908E-06B03E0B39F9}")
    if view2:
        mask = FWF_AUTOARRANGE | FWF_SNAPTOGRID
        _com(view2, 24, ctypes.c_long, [ctypes.c_uint, ctypes.c_uint])(
            view2, mask, FWF_SNAPTOGRID
        )
        _release(view2)


def _spacing_and_rows(folder_view) -> tuple[tuple[int, int], tuple[int, int], int]:
    import ctypes
    from ctypes import wintypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    hr = _com(folder_view, 12, ctypes.c_long, [ctypes.c_void_p])(folder_view, ctypes.byref(pt))
    if hr == 0 and pt.x > 0 and pt.y > 0:
        spacing = (int(pt.x), int(pt.y))
    else:
        spacing = _icon_metrics()[1]
    work = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0)
    rows = max(1, (work.bottom - work.top - 16) // max(48, spacing[1]))
    return (0, 0), spacing, rows


def _arrange_via_folderview(shortcuts: list[Path], folders: list[Path]) -> int:
    import ctypes

    folder_view = _folder_view()
    if not folder_view:
        return 0
    try:
        _prepare_custom_layout(folder_view)
        iid_folder = _guid("{000214E6-0000-0000-C000-000000000046}")
        folder = ctypes.c_void_p()
        hr = _com(folder_view, 5, ctypes.c_long, [ctypes.c_void_p, ctypes.c_void_p])(
            folder_view, ctypes.byref(iid_folder), ctypes.byref(folder)
        )
        if hr != 0 or not folder.value:
            return 0
        try:
            count = ctypes.c_int()
            hr = _com(folder_view, 7, ctypes.c_long, [ctypes.c_uint, ctypes.c_void_p])(
                folder_view, SVGIO_ALLVIEW, ctypes.byref(count)
            )
            if hr != 0 or count.value <= 0:
                return 0

            pidls: list[int] = []
            names: list[str] = []
            parsing: list[str | None] = []
            for index in range(count.value):
                pidl = ctypes.c_void_p()
                hr = _com(folder_view, 6, ctypes.c_long, [ctypes.c_int, ctypes.c_void_p])(
                    folder_view, index, ctypes.byref(pidl)
                )
                if hr != 0 or not pidl.value:
                    continue
                pidls.append(pidl.value)
                names.append(_display_name(folder.value, pidl.value, SHGDN_NORMAL))
                parsing.append(_display_name(folder.value, pidl.value, SHGDN_FORPARSING) or None)

            order = group_icon_names(names, shortcuts, folders, parsing)
            origin, spacing, rows = _spacing_and_rows(folder_view)
            positions = grid_positions(len(order), origin, spacing, rows)

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pidl_array = (ctypes.c_void_p * len(order))(*[pidls[i] for i in order])
            points = (POINT * len(order))(*[POINT(x, y) for x, y in positions])
            hr = _com(
                folder_view,
                16,
                ctypes.c_long,
                [ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint],
            )(
                folder_view,
                len(order),
                pidl_array,
                ctypes.byref(points),
                SVSI_POSITIONITEM,
            )
            for pidl in pidls:
                ctypes.windll.ole32.CoTaskMemFree(pidl)
            if hr != 0:
                return 0
            ctypes.windll.shell32.SHChangeNotify(0x8000000, 0x1000, None, None)
            return len(shortcuts) + len(folders)
        finally:
            _release(folder.value)
    finally:
        _release(folder_view)


def _desktop_defview():
    import ctypes

    user32 = ctypes.windll.user32
    user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.FindWindowExW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
    ]
    user32.FindWindowExW.restype = ctypes.c_void_p

    progman = user32.FindWindowW("Progman", None)
    defview = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
    if defview:
        return defview
    worker = None
    while True:
        worker = user32.FindWindowExW(None, worker, "WorkerW", None)
        if not worker:
            return None
        defview = user32.FindWindowExW(worker, None, "SHELLDLL_DefView", None)
        if defview:
            return defview


def _desktop_listview(defview):
    import ctypes

    user32 = ctypes.windll.user32
    user32.FindWindowExW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
    ]
    user32.FindWindowExW.restype = ctypes.c_void_p
    return user32.FindWindowExW(defview, None, "SysListView32", None)


def _listview_names(listview) -> list[str]:
    import ctypes
    from ctypes import wintypes

    class LVITEMW(ctypes.Structure):
        _fields_ = [
            ("mask", ctypes.c_uint),
            ("iItem", ctypes.c_int),
            ("iSubItem", ctypes.c_int),
            ("state", ctypes.c_uint),
            ("stateMask", ctypes.c_uint),
            ("pszText", ctypes.c_void_p),
            ("cchTextMax", ctypes.c_int),
            ("iImage", ctypes.c_int),
            ("lParam", ctypes.c_void_p),
            ("iIndent", ctypes.c_int),
            ("iGroupId", ctypes.c_int),
            ("cColumns", ctypes.c_uint),
            ("puColumns", ctypes.c_void_p),
            ("piColFmt", ctypes.c_void_p),
            ("iGroup", ctypes.c_int),
        ]

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
    user32.SendMessageW.restype = ctypes.c_size_t
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.VirtualAllocEx.restype = ctypes.c_void_p
    kernel32.VirtualAllocEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel32.WriteProcessMemory.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
    ]
    kernel32.ReadProcessMemory.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
    ]
    kernel32.VirtualFreeEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(listview, ctypes.byref(pid))
    process = kernel32.OpenProcess(0x0438, False, pid)
    if not process:
        return []
    try:
        count = int(user32.SendMessageW(listview, 0x1004, 0, 0))
        names: list[str] = []
        text_chars = 260
        item_size = ctypes.sizeof(LVITEMW)
        text_bytes = text_chars * 2
        remote = kernel32.VirtualAllocEx(process, None, item_size + text_bytes, 0x1000, 0x04)
        if not remote:
            return []
        try:
            text_ptr = remote + item_size
            for index in range(count):
                item = LVITEMW()
                item.mask = 0x0001
                item.iItem = index
                item.iSubItem = 0
                item.pszText = text_ptr
                item.cchTextMax = text_chars
                kernel32.WriteProcessMemory(process, remote, ctypes.byref(item), item_size, None)
                user32.SendMessageW(listview, 0x1073, index, remote)
                buf = ctypes.create_unicode_buffer(text_chars)
                kernel32.ReadProcessMemory(process, text_ptr, buf, text_bytes, None)
                names.append(buf.value)
        finally:
            kernel32.VirtualFreeEx(process, remote, 0, 0x8000)
        return names
    finally:
        kernel32.CloseHandle(process)


def _icon_metrics() -> tuple[tuple[int, int], tuple[int, int], int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    dx = ctypes.c_int()
    dy = ctypes.c_int()
    work = wintypes.RECT()
    user32.SystemParametersInfoW(13, 0, ctypes.byref(dx), 0)
    user32.SystemParametersInfoW(24, 0, ctypes.byref(dy), 0)
    user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0)
    spacing_x = max(48, int(dx.value) or 75)
    spacing_y = max(48, int(dy.value) or 75)
    rows = max(1, (work.bottom - work.top - 16) // spacing_y)
    return (0, 0), (spacing_x, spacing_y), rows


def _set_auto_arrange(defview, listview, enabled: bool) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
    user32.SendMessageW.restype = ctypes.c_size_t
    style = user32.GetWindowLongW(listview, -16)
    is_on = bool(style & 0x0100)
    if is_on != enabled:
        user32.SendMessageW(defview, 0x0111, 0x7041, 0)


def _arrange_via_listview(shortcuts: list[Path], folders: list[Path]) -> int:
    import ctypes

    defview = _desktop_defview()
    if not defview:
        return 0
    listview = _desktop_listview(defview)
    if not listview:
        return 0
    names = _listview_names(listview)
    if not names:
        return 0
    sequence = group_icon_names(names, shortcuts, folders)
    if not sequence:
        return 0
    _set_auto_arrange(defview, listview, False)
    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_size_t]
    user32.SendMessageW.restype = ctypes.c_size_t
    origin, spacing, rows = _icon_metrics()
    positions = grid_positions(len(sequence), origin, spacing, rows)
    for index, (x, y) in zip(sequence, positions, strict=False):
        packed = (y << 16) | (x & 0xFFFF)
        user32.SendMessageW(listview, 0x100F, index, packed)
    ctypes.windll.shell32.SHChangeNotify(0x8000000, 0x1000, None, None)
    return len(shortcuts) + len(folders)
