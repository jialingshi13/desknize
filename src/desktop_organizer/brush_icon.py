"""生成图2风格：蓝底圆角方块上的白色刷子图标。"""

from __future__ import annotations

import struct
from pathlib import Path

BLUE = (45, 110, 242, 255)
WHITE = (255, 255, 255, 255)
SHADOW = (18, 28, 56, 70)
CLEAR = (0, 0, 0, 0)
ICON_SIZES = (16, 32, 48, 64, 256)


def _pixel(px: list[list[tuple[int, int, int, int]]], x: int, y: int, color: tuple[int, int, int, int]) -> None:
    size = len(px)
    if 0 <= x < size and 0 <= y < size:
        src_a = color[3] / 255
        if src_a >= 0.99:
            px[y][x] = color
            return
        r, g, b, a = px[y][x]
        out_a = src_a + (a / 255) * (1 - src_a)
        if out_a <= 0:
            return
        px[y][x] = (
            int((color[0] * src_a + r * (a / 255) * (1 - src_a)) / out_a),
            int((color[1] * src_a + g * (a / 255) * (1 - src_a)) / out_a),
            int((color[2] * src_a + b * (a / 255) * (1 - src_a)) / out_a),
            int(out_a * 255),
        )


def _in_rounded_rect(x: float, y: float, left: float, top: float, right: float, bottom: float, radius: float) -> bool:
    if x < left or x > right or y < top or y > bottom:
        return False
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    if abs(x - cx) <= 0.001 or abs(y - cy) <= 0.001:
        return True
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def _scale(value: float, size: int) -> float:
    return value * size / 64.0


def render_brush(size: int = 64) -> list[list[tuple[int, int, int, int]]]:
    px = [[CLEAR for _ in range(size)] for _ in range(size)]
    pad = _scale(3.2, size)
    radius = _scale(15.4, size)
    for y in range(size):
        for x in range(size):
            if _in_rounded_rect(x - _scale(1.8, size), y - _scale(2.2, size), pad, pad, size - pad, size - pad, radius):
                _pixel(px, x, y, SHADOW)
    for y in range(size):
        for x in range(size):
            if _in_rounded_rect(x, y, pad, pad, size - pad, size - pad, radius):
                _pixel(px, x, y, BLUE)
    for y in range(size):
        for x in range(size):
            fx, fy = x + 0.5, y + 0.5
            if _in_bristles(fx, fy, size) or _in_ferrule(fx, fy, size) or _in_handle(fx, fy, size):
                _pixel(px, x, y, WHITE)
    return px


def _in_bristles(x: float, y: float, size: int) -> bool:
    top, bottom = _scale(9.2, size), _scale(22.4, size)
    if not (top <= y <= bottom):
        return False
    t = (y - top) / (bottom - top)
    left = _scale(16.4, size) + t * _scale(4.6, size)
    right = _scale(47.6, size) - t * _scale(4.6, size)
    return left <= x <= right


def _in_ferrule(x: float, y: float, size: int) -> bool:
    return _in_rounded_rect(
        x,
        y,
        _scale(19.2, size),
        _scale(24.6, size),
        _scale(44.8, size),
        _scale(32.0, size),
        _scale(3.4, size),
    )


def _in_handle(x: float, y: float, size: int) -> bool:
    return _in_rounded_rect(
        x,
        y,
        _scale(28.3, size),
        _scale(31.4, size),
        _scale(35.7, size),
        _scale(54.6, size),
        _scale(3.7, size),
    )


def _bgra_and_mask(px: list[list[tuple[int, int, int, int]]]) -> tuple[bytes, bytes]:
    size = len(px)
    xor = bytearray()
    mask = bytearray()
    for y in range(size - 1, -1, -1):
        row_bits = 0
        bit = 7
        for x in range(size):
            r, g, b, a = px[y][x]
            xor.extend((b, g, r, a))
            if a < 128:
                row_bits |= 1 << bit
            bit -= 1
            if bit < 0:
                mask.append(row_bits)
                row_bits = 0
                bit = 7
        if bit != 7:
            mask.append(row_bits)
        while len(mask) % 4:
            mask.append(0)
    return bytes(xor), bytes(mask)


def _icon_image(size: int) -> bytes:
    px = render_brush(size)
    xor, mask = _bgra_and_mask(px)
    header = struct.pack("<IIIHHIIIIII", 40, size, size * 2, 1, 32, 0, len(xor), 0, 0, 0, 0)
    return header + xor + mask


def write_ico(path: Path) -> Path:
    images = [_icon_image(size) for size in ICON_SIZES]
    count = len(images)
    offset = 6 + 16 * count
    entries = bytearray()
    for size, image in zip(ICON_SIZES, images, strict=True):
        width = 0 if size >= 256 else size
        height = 0 if size >= 256 else size
        entries.extend(struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(image), offset))
        offset += len(image)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.ico")
    tmp.write_bytes(struct.pack("<HHH", 0, 1, count) + bytes(entries) + b"".join(images))
    try:
        tmp.replace(path)
    except OSError:
        path.write_bytes(tmp.read_bytes())
        tmp.unlink(missing_ok=True)
    return path
