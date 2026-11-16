"""Chapter titles (CHAPTER.BMX 12-21): keep them centered when their width
changes.

The chapter screen script (CHAPTER1..9.TTM, CHAPTERE.TTM) draws the title with
DRAW_SPRITE (0xA500: x, y, image, 0) at an x of its own: the English titles
are centered by it. A translated title of another width is moved so that its
center stays where the center of the English one was (the original titles are
not exactly at the middle of the screen), within the screen.

TTM: tags VER:, PAG:, TT3:, TTI:...; TT3: u8 compression (1 = RLE), u32 size,
the RLE data (BaKGL bak/scene/scene.cpp). A command is u16 code | number of
u16 arguments (0xF: a string). The x is patched in place inside an RLE literal,
the file size does not change.
"""

from __future__ import annotations

import struct
from pathlib import Path

DRAW_SPRITE = 0xA500
TITLES = range(12, 22)
SCRIPTS = [f"CHAPTER{n}.TTM" for n in range(1, 10)] + ["CHAPTERE.TTM"]
SCREEN_WIDTH = 320


def _title_x(data: bytes) -> tuple[int, int, int]:
    """(image, x, file offset of x) of the title sprite of a chapter script."""
    tt3 = data.index(b"TT3:")
    p = tt3 + 8
    if data[p] != 1:
        raise ValueError("TT3 is not RLE")
    (size,) = struct.unpack_from("<I", data, p + 1)
    out = bytearray()
    source: list[int | None] = []  # file offset of every unpacked byte, None in a run
    q = p + 5
    while len(out) < size:
        c = data[q]
        q += 1
        if c & 0x80:
            out += bytes([data[q]]) * (c & 0x7F)
            source += [None] * (c & 0x7F)
            q += 1
        else:
            out += data[q : q + c]
            source += range(q, q + c)
            q += c
    p = 0
    while p < len(out):
        (code,) = struct.unpack_from("<H", out, p)
        p += 2
        count, code = code & 0xF, code & 0xFFF0
        if count == 0xF:
            end = out.index(0, p) + 1
            p = end + end % 2
            continue
        args = struct.unpack_from(f"<{count}h", out, p)
        if code == DRAW_SPRITE and count == 4 and args[2] in TITLES:
            where = source[p], source[p + 1]
            if None in where or where[1] != where[0] + 1:
                raise ValueError("the x of the title is not in an RLE literal")
            return args[2], args[0], where[0]
        p += 2 * count
    raise ValueError("no title sprite")


def center_titles(
    scripts_dir: Path, old_widths: dict[int, int], new_widths: dict[int, int]
) -> list[str]:
    """Move the titles whose width changes (image -> width); returns a report."""
    report = []
    for name in SCRIPTS:
        path = scripts_dir / name
        data = bytearray(path.read_bytes())
        image, x, pos = _title_x(data)
        if image not in new_widths or new_widths[image] == old_widths[image]:
            continue
        old, new = old_widths[image], new_widths[image]
        if new > SCREEN_WIDTH:
            raise ValueError(f"CHAPTER.BMX_{image}: {new} px is wider than the screen")
        center2 = 2 * x + old  # twice the center of the English title
        new_x = min(max((center2 - new) // 2, 0), SCREEN_WIDTH - new)
        assert struct.unpack_from("<h", data, pos)[0] == x
        struct.pack_into("<h", data, pos, new_x)
        path.write_bytes(bytes(data))
        report.append(
            f"{name}: CHAPTER.BMX_{image} {old} -> {new} px, x {x} -> {new_x}"
        )
    return report
