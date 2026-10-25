"""Item names (OBJINFO.DAT): export to CSV and import a translation.

OBJINFO.DAT is an array of 80-byte records, one per item (record 0 is empty),
followed by data that is not item records. The item name is the first field:
a zero-terminated string in 30 bytes. The u16 at 0x22 is the index of the
space where the name is split into two lines (shop, containers), 0 = one line;
the game puts \0 there while drawing and writes a space back. Item
descriptions are dialog snippets (DIAL_Z18.DDX, see `baktt dialog`).

On import the split is recalculated for the translated name: at "|" if the
translator put one there, otherwise at the space that balances the two lines
by width (GAME.FNT) - if the English name was split or the translated one is
wider than the widest one-line English name.
"""

from __future__ import annotations

import struct
from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.fonts import Font
from baktt.table import Row, load_translations, write_table

app = App(name="objinfo", help="Operations on item names (OBJINFO.DAT)")

FILENAME = "OBJINFO.DAT"
RECORD_SIZE = 80
NAME_SIZE = 30
SPLIT_POS = 0x22
SPLIT_MARK = "|"
# the widest English name shown on one line (Guilder's Passkey, GAME.FNT)
ONE_LINE_MAX_WIDTH = 76
ITEM_COUNT = 138


def read_names(data: bytes) -> list[str]:
    names = []
    for i in range(ITEM_COUNT):
        field = data[i * RECORD_SIZE : i * RECORD_SIZE + NAME_SIZE]
        name, _, padding = field.partition(b"\0")
        if padding.strip(b"\0"):
            raise ValueError(f"item {i}: unexpected bytes after the name: {field!r}")
        names.append(decode(name))
    return names


def write_name(data: bytearray, index: int, name: str) -> None:
    encoded = encode(name)
    if len(encoded) >= NAME_SIZE:
        raise ValueError(
            f"item {index}: name {name!r} is {len(encoded)} bytes, max {NAME_SIZE - 1}"
        )
    start = index * RECORD_SIZE
    data[start : start + NAME_SIZE] = encoded.ljust(NAME_SIZE, b"\0")


def _width(font: Font, text: bytes) -> int:
    width = 0
    for c in text:
        index = c - font.first
        if not 0 <= index < len(font.glyphs):
            raise ValueError(f"no glyph for byte 0x{c:02X} in {font.name}")
        width += font.glyphs[index].width
    return width


def split_position(name: str, was_split: bool, font: Font) -> tuple[str, int]:
    """(name without the split mark, index of the space to split at or 0)."""
    if SPLIT_MARK in name:
        index = name.index(SPLIT_MARK)
        return name.replace(SPLIT_MARK, " ", 1), index
    encoded = encode(name)
    spaces = [i for i, c in enumerate(encoded) if c == 0x20]
    if not spaces or not (was_split or _width(font, encoded) > ONE_LINE_MAX_WIDTH):
        return name, 0
    best = min(
        spaces,
        key=lambda i: max(_width(font, encoded[:i]), _width(font, encoded[i + 1 :])),
    )
    return name, best


def _key(index: int) -> str:
    return f"OBJINFO:{index:03d}"


NOTE = (
    "Не длиннее 29 знаков. У торговца делится на 2 строки: "
    "место переноса — «|» вместо пробела."
)


@app.command(name="export")
def export_command(src_dir: Path, table_path: Path) -> None:
    """Export item names to a table (.xlsx or .csv)."""
    names = read_names((src_dir / FILENAME).read_bytes())
    rows = [Row(_key(i), name, note=NOTE) for i, name in enumerate(names) if name]
    print(f"{write_table(table_path, rows)} item names exported to {table_path}")


@app.command(name="import")
def import_command(
    src_dir: Path, imported_dir: Path, table_path: Path, font: Path | None = None
) -> None:
    """Build OBJINFO.DAT with translated names (empty = keep original).

    "|" in a name marks where to split it into two lines. Widths are measured
    with `font` (default: GAME.FNT from src_dir; pass the Russian font).
    """
    import_table(src_dir, imported_dir, table_path, font)


def import_table(
    src_dir: Path, imported_dir: Path, table_path: Path, font_path: Path | None = None
) -> None:
    font = Font.from_file(font_path or src_dir / "GAME.FNT")
    data = bytearray((src_dir / FILENAME).read_bytes())
    names = read_names(bytes(data))
    translations = load_translations(table_path)
    errors: list[str] = []
    used = 0
    for i, name in enumerate(names):
        key = _key(i)
        if key not in translations:
            continue
        english, russian = translations[key]
        if english != name:
            errors.append(f"{key}: english text does not match the game file")
            continue
        if not russian.strip():
            continue
        try:
            start = i * RECORD_SIZE
            (old_split,) = struct.unpack_from("<H", data, start + SPLIT_POS)
            russian, split = split_position(russian.strip(), old_split != 0, font)
            write_name(data, i, russian)
            struct.pack_into("<H", data, start + SPLIT_POS, split)
        except ValueError as e:
            errors.append(f"{key}: {e}")
            continue
        used += 1
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    imported_dir.mkdir(parents=True, exist_ok=True)
    (imported_dir / FILENAME).write_bytes(data)
    print(f"{used} item names imported into {imported_dir}")
