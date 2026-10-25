"""Combat names (MNAMES.DAT): monsters and party members in combat.

Format: u16 count, count x u16 string offsets (relative to the string pool;
unused entries point to "INVALID MONSTER" at 0), u16 file size, then
zero-terminated strings. On import the pool is rebuilt and offsets are
relocated.
"""

from __future__ import annotations

import struct
from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.table import Row, load_translations, write_table

app = App(name="mnames", help="Operations on combat names (MNAMES.DAT)")

FILENAME = "MNAMES.DAT"


class MonsterNames:
    def __init__(self, data: bytes) -> None:
        (count,) = struct.unpack_from("<H", data, 0)
        self.offsets = list(struct.unpack_from(f"<{count}H", data, 2))
        self.pool_start = 2 + 2 * count + 2
        (size,) = struct.unpack_from("<H", data, 2 + 2 * count)
        if size != len(data):
            raise ValueError(f"size field {size} != file size {len(data)}")
        self.strings: dict[int, bytes] = {}  # pool-relative offset -> string
        p = self.pool_start
        while p < len(data):
            end = data.index(b"\0", p)
            self.strings[p - self.pool_start] = data[p:end]
            p = end + 1
        for i, offset in enumerate(self.offsets):
            if offset not in self.strings:
                raise ValueError(f"entry {i} = 0x{offset:X} is not a string start")

    def to_bytes(self) -> bytes:
        new_offset: dict[int, int] = {}
        pool = bytearray()
        for offset, text in self.strings.items():
            new_offset[offset] = len(pool)
            pool += text + b"\0"
        size = self.pool_start + len(pool)
        if size > 0xFFFF:
            raise ValueError(f"{FILENAME} would be {size} bytes, max 65535")
        offsets = [new_offset[o] for o in self.offsets]
        return struct.pack(f"<H{len(offsets)}HH", len(offsets), *offsets, size) + bytes(
            pool
        )

    def rows(self) -> list[tuple[int, int]]:
        """(entry, offset) of every string, by its first entry."""
        seen: set[int] = set()
        rows = []
        for i, offset in enumerate(self.offsets):
            if offset not in seen and self.strings[offset]:
                seen.add(offset)
                rows.append((i, offset))
        return rows


def _key(index: int) -> str:
    return f"MNAMES:{index:03d}"


# the name is substituted for @1 in the dialogs before a fight (BaKGL: text
# variable 16, the current monster)
NOTE = "Подставляется в реплики перед боем вместо @1, только в именительном падеже."


@app.command(name="export")
def export_command(src_dir: Path, table_path: Path) -> None:
    """Export monster names to a table (.xlsx or .csv)."""
    names = MonsterNames((src_dir / FILENAME).read_bytes())
    rows = [
        Row(_key(i), decode(names.strings[offset]), note=NOTE)
        for i, offset in names.rows()
    ]
    print(f"{write_table(table_path, rows)} names exported to {table_path}")


@app.command(name="import")
def import_command(src_dir: Path, imported_dir: Path, table_path: Path) -> None:
    """Build MNAMES.DAT with the translation from a table (empty = keep original)."""
    import_table(src_dir, imported_dir, table_path)


def import_table(src_dir: Path, imported_dir: Path, table_path: Path) -> None:
    names = MonsterNames((src_dir / FILENAME).read_bytes())
    translations = load_translations(table_path)
    errors: list[str] = []
    used = 0
    for i, offset in names.rows():
        key = _key(i)
        if key not in translations:
            continue
        english, russian = translations[key]
        if english != decode(names.strings[offset]):
            errors.append(f"{key}: english text does not match the game file")
            continue
        if not russian.strip():
            continue
        try:
            names.strings[offset] = encode(russian)
        except ValueError as e:
            errors.append(f"{key}: {e}")
            continue
        used += 1
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    imported_dir.mkdir(parents=True, exist_ok=True)
    (imported_dir / FILENAME).write_bytes(names.to_bytes())
    print(f"{used} names imported into {imported_dir}")
