"""生成图2风格：蓝底圆角方块上的白色刷子图标。"""

from __future__ import annotations

import struct
from pathlib import Path

SIZE = 64
BLUE = (45, 110, 242, 255)
WHITE = (255, 255, 255, 255)
SHADOW = (18, 28, 56, 70)
CLEAR = (0, 0, 0, 0)


def _pixel(px: list[list[tuple[int, int, int, int]]], x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if 0 <= x < SIZE and 0 <= y < SIZE:
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


def _in_bristles(x: float, y: float) -> bool:
    top, bottom = 9.2, 22.4
    if not (top <= y <= bottom):
        return False
    t = (y - top) / (bottom - top)
    left = 16.4 + t * 4.6
    right = 47.6 - t * 4.6
    return left <= x <= right


def _in_ferrule(x: float, y: float) -> bool:
    return _in_rounded_rect(x, y, 19.2, 24.6, 44.8, 32.0, 3.4)


def _in_handle(x: float, y: float) -> bool:
    return _in_rounded_rect(x, y, 28.3, 31.4, 35.7, 54.6, 3.7)


def render_brush() -> list[list[tuple[int, int, int, int]]]:
    px = [[CLEAR for _ in range(SIZE)] for _ in range(SIZE)]
    pad = 3.2
    radius = 15.4
    for y in range(SIZE):
        for x in range(SIZE):
            if _in_rounded_rect(x - 1.8, y - 2.2, pad, pad, SIZE - pad, SIZE - pad, radius):
                _pixel(px, x, y, SHADOW)
    for y in range(SIZE):
        for x in range(SIZE):
            if _in_rounded_rect(x, y, pad, pad, SIZE - pad, SIZE - pad, radius):
                _pixel(px, x, y, BLUE)
    for y in range(SIZE):
        for x in range(SIZE):
            if _in_bristles(x + 0.5, y + 0.5) or _in_ferrule(x + 0.5, y + 0.5) or _in_handle(x + 0.5, y + 0.5):
                _pixel(px, x, y, WHITE)
    return px


def _bgra_and_mask(px: list[list[tuple[int, int, int, int]]]) -> tuple[bytes, bytes]:
    xor = bytearray()
    mask = bytearray()
    for y in range(SIZE - 1, -1, -1):
        row_bits = 0
        bit = 7
        for x in range(SIZE):
            r, g, b, a = px[y][x]
            xor.extend((b, g, r, a))
            if a < 128:
                row_bits |= 1 << bit
            bit -= 1
            if bit < 0:
                mask.append(row_bits)
                row_bits = 0
                bit = 7
        while len(mask) % 4:
            mask.append(0)
    return bytes(xor), bytes(mask)


def write_ico(path: Path) -> Path:
    px = render_brush()
    xor, mask = _bgra_and_mask(px)
    header = struct.pack("<IIIHHIIIIII", 40, SIZE, SIZE * 2, 1, 32, 0, len(xor), 0, 0, 0, 0)
    image = header + xor + mask
    icon_dir = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", SIZE, SIZE, 0, 0, 1, 32, len(image), 6 + 16)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(icon_dir + entry + image)
    return path
