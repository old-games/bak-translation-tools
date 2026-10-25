"""Keywords (KEYWORD.DAT): dialog topics, answer buttons and NPC names.

Format: u16 file size, then a table of u16 pointers up to the first string,
then zero-terminated strings. Several pointers may share one string. Pointer
0 points inside the table itself (to the second list), it is not a string.
BaKGL reads 347 pointers: 1..171 dialog topics, 241..291 answer buttons and
numbers, 300..346 NPC names (empty entries are unused).

On import the string pool is rebuilt (strings may change length) and string
pointers are relocated; pointers into the table are kept.
"""

from __future__ import annotations

import struct
from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.exe_patch import TOPIC_BUTTON_WIDTH
from baktt.fonts import Font
from baktt.table import Row, load_translations, write_table
from baktt.ui import text_width

app = App(name="keyword", help="Operations on dialog keywords (KEYWORD.DAT)")

FILENAME = "KEYWORD.DAT"
FONT = "GAME.FNT"
# Topics and answers are shown on buttons of a fixed size. Topic buttons are
# 70 px in the original (the longest English topic, "Rhuargh's room", is 70 px)
# and 76 px with the EXE patch (baktt.exe_patch); answer buttons are 70 px.
ANSWER_BUTTON_WIDTH = 70


def button_width(number: int) -> int | None:
    """Width limit of a keyword shown on a button (None: not a button)."""
    if 1 <= number <= 171:
        return TOPIC_BUTTON_WIDTH
    if 241 <= number <= 291:
        return ANSWER_BUTTON_WIDTH
    return None


class KeywordFile:
    def __init__(self, data: bytes) -> None:
        (size,) = struct.unpack_from("<H", data, 0)
        if size != len(data):
            raise ValueError(f"size field {size} != file size {len(data)}")
        self.pool_start = _find_pool_start(data)
        count = (self.pool_start - 2) // 2
        self.pointers = list(struct.unpack_from(f"<{count}H", data, 2))
        self.strings = _split_strings(data, self.pool_start)
        for i, pointer in enumerate(self.pointers):
            if pointer >= self.pool_start and pointer not in self.strings:
                raise ValueError(f"pointer {i} = 0x{pointer:X} is not a string start")

    def is_string(self, index: int) -> bool:
        return self.pointers[index] >= self.pool_start

    def to_bytes(self) -> bytes:
        new_offset: dict[int, int] = {}
        pool = bytearray()
        for offset, text in self.strings.items():
            new_offset[offset] = self.pool_start + len(pool)
            pool += text + b"\0"
        size = self.pool_start + len(pool)
        if size > 0xFFFF:
            raise ValueError(f"{FILENAME} would be {size} bytes, max 65535")
        pointers = [new_offset[p] if p >= self.pool_start else p for p in self.pointers]
        return (
            struct.pack("<H", size)
            + struct.pack(f"<{len(pointers)}H", *pointers)
            + bytes(pool)
        )


def _split_strings(data: bytes, start: int) -> dict[int, bytes]:
    """pool offset -> string (without the trailing zero), in file order"""
    strings = {}
    p = start
    while p < len(data):
        end = data.index(b"\0", p)
        strings[p] = data[p:end]
        p = end + 1
    return strings


def _find_pool_start(data: bytes) -> int:
    """The smallest pointer value such that everything before it is the pointer
    table, everything after it is strings, every pointer beyond the table hits
    a string start and every string is referenced."""
    if not data.endswith(b"\0"):
        raise ValueError("the file does not end with a string terminator")
    values = struct.unpack_from(f"<{(len(data) - 2) // 2}H", data, 2)
    for start in sorted({v for v in values if 2 < v < len(data) and v % 2 == 0}):
        pointers = values[: (start - 2) // 2]
        strings = _split_strings(data, start)
        referenced = {p for p in pointers if p >= start}
        if referenced == set(strings):
            return start
    raise ValueError("cannot find the start of the strings")


def _key(index: int) -> str:
    return f"KEYWORD:{index:03d}"


def _rows(keywords: KeywordFile) -> list[tuple[int, int]]:
    """(index, pool offset) of every non-empty string, by its first pointer."""
    seen: set[int] = set()
    rows = []
    for i, pointer in enumerate(keywords.pointers):
        if keywords.is_string(i) and pointer not in seen and keywords.strings[pointer]:
            seen.add(pointer)
            rows.append((i, pointer))
    return rows


@app.command(name="export")
def export_command(src_dir: Path, table_path: Path) -> None:
    """Export keywords to a table (.xlsx or .csv); the note of a topic or an
    answer gives the button width limit."""
    keywords = KeywordFile((src_dir / FILENAME).read_bytes())
    font = Font.from_file(src_dir / FONT)
    rows = []
    for i, pointer in _rows(keywords):
        text = keywords.strings[pointer]
        note = ""
        limit = button_width(i)
        if limit:
            width = text_width(font, text)
            note = (
                f"Не шире {limit} px (английский — {width} px): "
                "кнопка не растягивается."
            )
        rows.append(Row(_key(i), decode(text), note=note))
    print(f"{write_table(table_path, rows)} keywords exported to {table_path}")


@app.command(name="import")
def import_command(
    src_dir: Path, imported_dir: Path, table_path: Path, font: Path | None = None
) -> None:
    """Build KEYWORD.DAT with the translation from a table (empty = keep original).

    Topics and answers are measured with `font` (default: GAME.FNT from
    src_dir; pass the Russian font) and must fit the button.
    """
    import_table(src_dir, imported_dir, table_path, font)


def import_table(
    src_dir: Path, imported_dir: Path, table_path: Path, font_path: Path | None = None
) -> None:
    keywords = KeywordFile((src_dir / FILENAME).read_bytes())
    font = Font.from_file(font_path or src_dir / FONT)
    translations = load_translations(table_path)
    errors: list[str] = []
    used = 0
    for i, pointer in _rows(keywords):
        key = _key(i)
        if key not in translations:
            continue
        english, russian = translations[key]
        if english != decode(keywords.strings[pointer]):
            errors.append(f"{key}: english text does not match the game file")
            continue
        if not russian.strip():
            continue
        try:
            encoded = encode(russian)
        except ValueError as e:
            errors.append(f"{key}: {e}")
            continue
        limit = button_width(i)
        if limit and text_width(font, encoded) > limit:
            errors.append(
                f"{key}: {russian!r} is {text_width(font, encoded)} px wide, "
                f"max {limit} px"
            )
            continue
        keywords.strings[pointer] = encoded
        used += 1
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    imported_dir.mkdir(parents=True, exist_ok=True)
    (imported_dir / FILENAME).write_bytes(keywords.to_bytes())
    print(f"{used} keywords imported into {imported_dir}")
