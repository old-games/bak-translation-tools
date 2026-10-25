"""Party member names in STARTUP.GAM (the new game save, not in krondor.001).

Names are zero-padded 10-byte fields (at most 9 bytes of text) at 0x9F:
Locklear, Gorath, Owyn, Pug, James, Patrus. The game substitutes them for @
in dialogs and item descriptions. Combat names are in MNAMES.DAT.
"""

from __future__ import annotations

from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.table import Row, load_translations, write_table

app = App(name="party", help="Party member names in STARTUP.GAM")

NAMES_OFFSET = 0x9F
NAME_SIZE = 10
NAME_COUNT = 6


def read_names(data: bytes) -> list[str]:
    names = []
    for i in range(NAME_COUNT):
        start = NAMES_OFFSET + NAME_SIZE * i
        name, _, padding = data[start : start + NAME_SIZE].partition(b"\0")
        if not name or padding.strip(b"\0"):
            raise ValueError(
                f"unexpected name field {i}: {data[start : start + NAME_SIZE]!r}"
            )
        names.append(decode(name))
    return names


def _key(index: int) -> str:
    return f"PARTY:{index}"


@app.command(name="export")
def export_command(startup_gam: Path, table_path: Path) -> None:
    """Export party member names to a table (.xlsx or .csv)."""
    names = read_names(startup_gam.read_bytes())
    rows = [
        Row(_key(i), name, note="Не длиннее 9 знаков.") for i, name in enumerate(names)
    ]
    print(f"{write_table(table_path, rows)} names exported to {table_path}")


@app.command(name="import")
def import_command(startup_gam: Path, table_path: Path) -> None:
    """Write translated party member names into STARTUP.GAM in place."""
    import_table(startup_gam, table_path)


def import_table(startup_gam: Path, table_path: Path) -> None:
    data = bytearray(startup_gam.read_bytes())
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
        encoded = encode(russian)
        if not 0 < len(encoded) < NAME_SIZE:
            errors.append(
                f"{key}: {russian!r} is {len(encoded)} bytes, max {NAME_SIZE - 1}"
            )
            continue
        start = NAMES_OFFSET + NAME_SIZE * i
        data[start : start + NAME_SIZE] = encoded.ljust(NAME_SIZE, b"\0")
        used += 1
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    startup_gam.write_bytes(data)
    print(f"{used} party names written to {startup_gam}")
