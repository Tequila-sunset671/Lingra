"""Генерирует icon_1024.png (микрофон на градиенте) без сторонних библиотек.

Используется только stdlib (zlib + struct). Дальше build_app.sh делает из него
.icns через sips + iconutil.
"""

import struct
import zlib
from pathlib import Path

W = 1024
TOP = (124, 92, 246)   # фиолетовый
BOT = (59, 130, 246)   # синий
WHITE = (255, 255, 255)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def in_rrect(px, py, x0, y0, x1, y1, r):
    """Точка внутри прямоугольника со скруглёнными углами (радиус r)."""
    cx = clamp(px, x0 + r, x1 - r)
    cy = clamp(py, y0 + r, y1 - r)
    dx, dy = px - cx, py - cy
    return dx * dx + dy * dy <= r * r


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_rows():
    rows = []
    for y in range(W):
        row = bytearray()
        row.append(0)  # filter type 0
        grad = lerp(TOP, BOT, y / (W - 1))
        for x in range(W):
            if not in_rrect(x, y, 0, 0, W - 1, W - 1, 225):
                row += b"\x00\x00\x00\x00"  # прозрачный фон вне скруглённого квадрата
                continue
            # Микрофон поверх градиента
            body = in_rrect(x, y, 412, 250, 612, 560, 100)      # капсула
            stem = in_rrect(x, y, 497, 558, 527, 705, 10)       # ножка
            base = in_rrect(x, y, 422, 700, 602, 732, 14)       # подставка
            # дужка-кронштейн вокруг капсулы (внешнее кольцо минус внутреннее)
            dx, dy = x - 512, y - 470
            d2 = dx * dx + dy * dy
            bracket = (155 * 155 <= d2 <= 185 * 185) and y >= 360
            if body or stem or base or bracket:
                row += bytes(WHITE) + b"\xff"
            else:
                row += bytes(grad) + b"\xff"
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path, raw):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, W, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    Path(path).write_bytes(png)


if __name__ == "__main__":
    out = Path(__file__).with_name("icon_1024.png")
    write_png(out, build_rows())
    print(out)
