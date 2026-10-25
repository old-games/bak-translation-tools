"""UI texts: buttons (REQ_*.DAT), labels (LBL_*.DAT) and IN_SAVE.DAT.

REQ: 28-byte window header, u16 count, count x 33-byte widget records (label
offset at +21, -1 = no label), u16 pool size, string pool.
LBL: u16 count, count x 10-byte records (label offset at +0), u16 pool size,
string pool.
IN: u16 pool size, string pool, u16 count, count x 21-byte records (label
offset at +13).

Offsets are relative to the pool. Some pool strings are not referenced by any
record (e.g. the line after a teleport destination in REQ_TELE.DAT), so all
strings are exported, keyed by their original pool offset, and the pool order
is kept on rebuild.

Buttons do not grow with their text, so on import every button label is
measured with the game font (GAME.FNT) and must be at most the button width
minus BUTTON_PADDING (the smallest margin of the original labels is 5 px).
"""

from __future__ import annotations

import struct
from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.fonts import Font
from baktt.table import Row, load_translations, write_table

app = App(name="ui", help="Operations on UI texts (REQ_*.DAT, LBL_*.DAT, IN_SAVE.DAT)")

# files that KRONDOR.EXE loads; the rest are leftovers of the developers' tools
USED_FILES = [
    "LBL_LOAD.DAT",
    "LBL_PREF.DAT",
    "LBL_SAVE.DAT",
    "IN_SAVE.DAT",
    "REQ_CAMP.DAT",
    "REQ_CAST.DAT",
    "REQ_CHET.DAT",
    "REQ_CMAP.DAT",
    "REQ_FMAP.DAT",
    "REQ_GDS.DAT",
    "REQ_HEAL.DAT",
    "REQ_INFO.DAT",
    "REQ_INV.DAT",
    "REQ_INV2.DAT",
    "REQ_KNOC.DAT",
    "REQ_LOAD.DAT",
    "REQ_MAIN.DAT",
    "REQ_MAP.DAT",
    "REQ_OPT0.DAT",
    "REQ_OPT1.DAT",
    "REQ_PREF.DAT",
    "REQ_PUZL.DAT",
    "REQ_SAVE.DAT",
    "REQ_TELE.DAT",
]

REQ_HEADER_SIZE = 28
REQ_RECORD_SIZE = 33
REQ_LABEL_POS = 21
REQ_WIDTH_POS = 15
LBL_RECORD_SIZE = 10
IN_RECORD_SIZE = 21
IN_LABEL_POS = 13

FONT = "GAME.FNT"
BUTTON_PADDING = 4
# labels that are not drawn inside their widget: teleport points on the map,
# a text input field
WIDTH_UNCHECKED = {"REQ_TELE.DAT", "REQ_INV2.DAT"}


class UIFile:
    def __init__(self, name: str, data: bytes) -> None:
        upper = name.upper()
        # REQ_/LBL_: records, then the pool; IN_: the pool, then records
        self.pool_first = upper.startswith("IN_")
        if upper.startswith("REQ_"):
            count_pos, record_size, label_pos = (
                REQ_HEADER_SIZE,
                REQ_RECORD_SIZE,
                REQ_LABEL_POS,
            )
        elif upper.startswith("LBL_"):
            count_pos, record_size, label_pos = 0, LBL_RECORD_SIZE, 0
        elif self.pool_first:
            count_pos, record_size, label_pos = 0, IN_RECORD_SIZE, IN_LABEL_POS
        else:
            raise ValueError(f"{name}: not a REQ_/LBL_/IN_ file")

        if self.pool_first:
            (pool_size,) = struct.unpack_from("<H", data, 0)
            pool = data[2 : 2 + pool_size]
            self.records = bytearray(data[2 + pool_size :])
        else:
            (count,) = struct.unpack_from("<H", data, count_pos)
            pool_size_pos = count_pos + 2 + record_size * count
            (pool_size,) = struct.unpack_from("<H", data, pool_size_pos)
            pool = data[pool_size_pos + 2 :]
            self.records = bytearray(data[:pool_size_pos])
        (count,) = struct.unpack_from("<H", self.records, count_pos)
        expected = count_pos + 2 + record_size * count
        if (
            pool_size != len(pool)
            or (pool and not pool.endswith(b"\0"))
            or (self.pool_first and len(self.records) != expected)
        ):
            raise ValueError(f"{name}: unexpected layout")
        # positions of label offsets in self.records
        self.label_positions = [
            count_pos + 2 + record_size * i + label_pos for i in range(count)
        ]
        self.strings: dict[int, bytes] = {}  # pool offset -> string, in order
        p = 0
        while p < len(pool):
            end = pool.index(b"\0", p)
            self.strings[p] = pool[p:end]
            p = end + 1
        # pool offset -> max label width in pixels
        self.max_widths: dict[int, int] = {}
        for pos in self.label_positions:
            (offset,) = struct.unpack_from("<h", self.records, pos)
            if offset == -1:
                continue
            if offset not in self.strings:
                raise ValueError(f"{name}: label offset {offset} is not a string")
            if upper.startswith("REQ_") and upper not in WIDTH_UNCHECKED:
                record = pos - REQ_LABEL_POS
                (width,) = struct.unpack_from(
                    "<H", self.records, record + REQ_WIDTH_POS
                )
                limit = width - BUTTON_PADDING
                self.max_widths[offset] = min(limit, self.max_widths.get(offset, limit))

    def to_bytes(self) -> bytes:
        new_offset: dict[int, int] = {}
        pool = bytearray()
        for offset, text in self.strings.items():
            new_offset[offset] = len(pool)
            pool += text + b"\0"
        records = bytearray(self.records)
        for pos in self.label_positions:
            (offset,) = struct.unpack_from("<h", records, pos)
            if offset != -1:
                struct.pack_into("<h", records, pos, new_offset[offset])
        if len(pool) > 0x7FFF:
            raise ValueError("string pool is too large")
        size = struct.pack("<H", len(pool))
        if self.pool_first:
            return size + bytes(pool) + bytes(records)
        return bytes(records) + size + bytes(pool)


def text_width(font: Font, text: bytes) -> int:
    width = 0
    for c in text:
        index = c - font.first
        if not 0 <= index < len(font.glyphs):
            raise ValueError(f"no glyph for byte 0x{c:02X} in {font.name}")
        width += font.glyphs[index].width
    return width


def _key(filename: str, offset: int) -> str:
    return f"{Path(filename).stem}:{offset:03d}"


@app.command(name="export")
def export_command(src_dir: Path, table_path: Path) -> None:
    """Export texts of the UI files used by the game to a table (.xlsx or .csv).

    The note of a button label: the maximum width and the width of the English
    text, in pixels.
    """
    font = Font.from_file(src_dir / FONT)
    rows = []
    for name in USED_FILES:
        ui = UIFile(name, (src_dir / name).read_bytes())
        for offset, text in ui.strings.items():
            if not text:
                continue
            note = ""
            if offset in ui.max_widths:
                note = (
                    f"Не шире {ui.max_widths[offset]} px (английский — "
                    f"{text_width(font, text)} px): кнопка не растягивается."
                )
            rows.append(Row(_key(name, offset), decode(text), note=note))
    print(f"{write_table(table_path, rows)} UI strings exported to {table_path}")


@app.command(name="import")
def import_command(
    src_dir: Path, imported_dir: Path, table_path: Path, font: Path | None = None
) -> None:
    """Build UI files with the translation from a table (empty = keep original).

    Button labels are measured with `font` (default: GAME.FNT from src_dir);
    pass the Russian font, e.g. data/modified/GAME.FNT.
    """
    import_table(src_dir, imported_dir, table_path, font)


def import_table(
    src_dir: Path, imported_dir: Path, table_path: Path, font_path: Path | None = None
) -> None:
    font = Font.from_file(font_path or src_dir / FONT)
    translations = load_translations(table_path)
    files = sorted({key.split(":")[0] + ".DAT" for key in translations})
    errors: list[str] = []
    used = 0
    imported_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        ui = UIFile(name, (src_dir / name).read_bytes())
        for offset, text in ui.strings.items():
            key = _key(name, offset)
            if key not in translations:
                continue
            english, russian = translations[key]
            if english != decode(text):
                errors.append(f"{key}: english text does not match the game file")
                continue
            if not russian.strip():
                continue
            try:
                encoded = encode(russian)
                width = text_width(font, encoded)
            except ValueError as e:
                errors.append(f"{key}: {e}")
                continue
            if offset in ui.max_widths and width > ui.max_widths[offset]:
                errors.append(
                    f"{key}: {russian!r} is {width} px wide, "
                    f"the button fits {ui.max_widths[offset]} px"
                )
                continue
            ui.strings[offset] = encoded
            used += 1
        (imported_dir / name).write_bytes(ui.to_bytes())
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    print(f"{used} UI strings imported into {imported_dir}")
