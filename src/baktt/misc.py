"""Spells, town names on the map and credits.

SPELLS.DAT    u16 count, count x 22-byte records (u16 name offset at +0),
              u16 file size, string pool (spell names).
SPELLDOC.DAT  u16 count, count x u32 offsets, u16 file size, string pool
              (7 strings per spell: name, cost, damage, duration, line of
              sight, description in two parts).
INVSPELL.DAT  6 groups: u16 unknown, u16 count, count x (char[24] name,
              u16 spell index) - names in fixed fields, at most 23 bytes.
FMAP_TWN.DAT  10-byte header (the last u16 is the town count), then
              records: u16 length, name (with \\0), u16 x, u16 y.
CRED.DAT      u16 count, count x u16 offsets (one per credits line, the
              empty string at 0 is an empty line), u16 file size, pool.

Pool strings are keyed by their original pool offset (some are not
referenced by any record, so all are kept in order); fixed and sequential
records are keyed by record number.
"""

from __future__ import annotations

import csv
import struct
from pathlib import Path

from cyclopts import App

from baktt.dialog import CSV_HEADER, load_translations
from baktt.encoding import decode, encode

app = App(
    name="misc", help="Spell names and descriptions, town names on the map, credits"
)


class PoolFile:
    """count, records with pool offsets, u16 file size, string pool."""

    def __init__(self, data: bytes, record_size: int, offset_format: str) -> None:
        (count,) = struct.unpack_from("<H", data, 0)
        self.offset_format = offset_format
        self.offset_positions = [2 + record_size * i for i in range(count)]
        self.size_pos = 2 + record_size * count
        (size,) = struct.unpack_from("<H", data, self.size_pos)
        if size != len(data) or not data.endswith(b"\0"):
            raise ValueError("unexpected file size field or string pool")
        self.head = bytearray(data[: self.size_pos])
        pool_start = self.size_pos + 2
        self.texts: dict[int, bytes] = {}  # pool offset -> string, in order
        p = pool_start
        while p < len(data):
            end = data.index(b"\0", p)
            self.texts[p - pool_start] = data[p:end]
            p = end + 1
        for pos in self.offset_positions:
            (offset,) = struct.unpack_from(offset_format, data, pos)
            if offset not in self.texts:
                raise ValueError(f"offset 0x{offset:X} is not a string start")

    def to_bytes(self) -> bytes:
        new_offset: dict[int, int] = {}
        pool = bytearray()
        for offset, text in self.texts.items():
            new_offset[offset] = len(pool)
            pool += text + b"\0"
        head = bytearray(self.head)
        for pos in self.offset_positions:
            (offset,) = struct.unpack_from(self.offset_format, head, pos)
            struct.pack_into(self.offset_format, head, pos, new_offset[offset])
        size = len(head) + 2 + len(pool)
        if size > 0xFFFF:
            raise ValueError(f"the file would be {size} bytes, max 65535")
        return bytes(head) + struct.pack("<H", size) + bytes(pool)


class InvSpellFile:
    GROUPS = 6
    NAME_SIZE = 24

    def __init__(self, data: bytes) -> None:
        self.data = bytearray(data)
        self.name_positions: list[int] = []
        p = 0
        for _ in range(self.GROUPS):
            (count,) = struct.unpack_from("<H", data, p + 2)
            p += 4
            for _ in range(count):
                self.name_positions.append(p)
                p += self.NAME_SIZE + 2
        if p != len(data):
            raise ValueError("unexpected INVSPELL.DAT layout")
        self.texts = {
            i: bytes(data[pos : pos + self.NAME_SIZE]).split(b"\0")[0]
            for i, pos in enumerate(self.name_positions)
        }

    def to_bytes(self) -> bytes:
        data = bytearray(self.data)
        for i, pos in enumerate(self.name_positions):
            text = self.texts[i]
            if len(text) >= self.NAME_SIZE:
                raise ValueError(
                    f"{text!r} is {len(text)} bytes, max {self.NAME_SIZE - 1}"
                )
            old = data[pos : pos + self.NAME_SIZE]
            if old.split(b"\0")[0] != text:  # keep the original padding if unchanged
                data[pos : pos + self.NAME_SIZE] = text.ljust(self.NAME_SIZE, b"\0")
        return bytes(data)


class TownMapFile:
    HEADER_SIZE = 10

    def __init__(self, data: bytes) -> None:
        self.header = data[: self.HEADER_SIZE]
        (count,) = struct.unpack_from("<H", data, self.HEADER_SIZE - 2)
        self.coords: list[bytes] = []
        self.texts: dict[int, bytes] = {}
        p = self.HEADER_SIZE
        for i in range(count):
            (length,) = struct.unpack_from("<H", data, p)
            name = data[p + 2 : p + 2 + length]
            if not name.endswith(b"\0"):
                raise ValueError(f"town {i}: name is not zero-terminated")
            self.texts[i] = name[:-1]
            self.coords.append(data[p + 2 + length : p + 6 + length])
            p += 6 + length
        if p != len(data):
            raise ValueError("unexpected FMAP_TWN.DAT layout")

    def to_bytes(self) -> bytes:
        out = bytearray(self.header)
        for i, coords in enumerate(self.coords):
            name = self.texts[i] + b"\0"
            out += struct.pack("<H", len(name)) + name + coords
        return bytes(out)


LOADERS = {
    "SPELLS.DAT": lambda data: PoolFile(data, 22, "<H"),
    "SPELLDOC.DAT": lambda data: PoolFile(data, 4, "<I"),
    "INVSPELL.DAT": InvSpellFile,
    "FMAP_TWN.DAT": TownMapFile,
    "CRED.DAT": lambda data: PoolFile(data, 2, "<H"),
}


def _key(filename: str, index: int) -> str:
    return f"{Path(filename).stem}:{index:04d}"


@app.command(name="export")
def export_command(src_dir: Path, csv_path: Path) -> None:
    """Export spell names, spell descriptions and town names to CSV."""
    rows = 0
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for name, loader in LOADERS.items():
            file = loader((src_dir / name).read_bytes())
            for index, text in file.texts.items():
                if text:
                    writer.writerow((_key(name, index), decode(text), ""))
                    rows += 1
    print(f"{rows} strings exported to {csv_path}")


@app.command(name="import")
def import_command(src_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    """Build the files with the translation from CSV (empty = keep original)."""
    import_csv(src_dir, imported_dir, csv_path)


def import_csv(src_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    translations = load_translations(csv_path)
    errors: list[str] = []
    used = 0
    imported_dir.mkdir(parents=True, exist_ok=True)
    for name, loader in LOADERS.items():
        file = loader((src_dir / name).read_bytes())
        for index, text in list(file.texts.items()):
            key = _key(name, index)
            if key not in translations:
                continue
            english, russian = translations[key]
            if english != decode(text):
                errors.append(f"{key}: english text does not match the game file")
                continue
            if not russian.strip():
                continue
            try:
                file.texts[index] = encode(russian)
            except ValueError as e:
                errors.append(f"{key}: {e}")
                continue
            used += 1
        try:
            (imported_dir / name).write_bytes(file.to_bytes())
        except ValueError as e:
            errors.append(f"{name}: {e}")
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    print(f"{used} strings imported into {imported_dir}")
