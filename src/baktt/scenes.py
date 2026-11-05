"""Scenes (GDS*.DAT): the mouse cursor of the hotspots.

GDS: 43-byte header (u16 hotspot count at +29), then 36-byte hotspot records:
x, y, w, h, u16 chapter mask, u16 cursor + 1 at +0x0A, u8 action at +0x0C, ...
(BaKGL bak/hotspot.cpp). The game turns every hotspot into a widget with the
cursor (overlay code at file 0x4031F: `mov ax,[di+0Ah]; dec ax`), the cursor is
an image of POINTERG.BMX; the hints over buildings ("Inn", "Shop") are cursors.

The same cursor 5 ("Inn") is used for entering an inn from the town and for
staying the night inside it, which need different words in Russian. Cursor 23
("Bar") is not used anywhere: no scene, no REQ widget (+0x1B) and no code
(the set cursor function 1A88:00A1/00B5 gets only 0, 2, -1 and these two), so
the night hotspots (action INN) get it, with the new image in POINTERG.BMX_23.
"""

from __future__ import annotations

import struct
from pathlib import Path

HEADER_SIZE = 43
COUNT_POS = 29
RECORD_SIZE = 36
CURSOR_POS = 0x0A  # cursor + 1
ACTION_POS = 0x0C
ACTION_INN = 7

INN_CURSOR = 5
NIGHT_CURSOR = 23
# the PNG that turns the free cursor into the night hint
NIGHT_CURSOR_IMAGE = f"POINTERG.BMX_{NIGHT_CURSOR}.png"
# scenes of the original with an INN hotspot showing the "Inn" cursor
NIGHT_HOTSPOTS = 17


def hotspots(data: bytes) -> list[int]:
    """Offsets of the hotspot records."""
    (count,) = struct.unpack_from("<H", data, COUNT_POS)
    if HEADER_SIZE + RECORD_SIZE * count != len(data):
        raise ValueError("unexpected GDS layout")
    return [HEADER_SIZE + RECORD_SIZE * i for i in range(count)]


def set_night_cursor(resources_dir: Path) -> int:
    """Give the INN hotspots with the "Inn" cursor the night cursor. Returns
    the number of changed hotspots."""
    changed = 0
    for path in sorted(resources_dir.glob("GDS*.DAT")):
        data = bytearray(path.read_bytes())
        found = False
        for pos in hotspots(data):
            (cursor,) = struct.unpack_from("<H", data, pos + CURSOR_POS)
            if cursor - 1 == NIGHT_CURSOR:
                raise ValueError(f"{path.name}: cursor {NIGHT_CURSOR} is already used")
            if data[pos + ACTION_POS] == ACTION_INN and cursor - 1 == INN_CURSOR:
                struct.pack_into("<H", data, pos + CURSOR_POS, NIGHT_CURSOR + 1)
                changed += 1
                found = True
        if found:
            path.write_bytes(bytes(data))
    if changed != NIGHT_HOTSPOTS:
        raise ValueError(
            f"{changed} night hotspots with the Inn cursor, expected {NIGHT_HOTSPOTS}"
        )
    return changed
