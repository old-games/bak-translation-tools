"""KRONDOR.EXE (v1.02) patches for the translation.

1. Font characters 0x80..0xDF.

The character width function (resident segment 0598:06A6, file offset 0x8426)
checks `0 <= c - first < count`, but all 8 of its call sites pass the
character sign-extended with `cbw`, so every byte >= 0x80 gets zero width
(word wrapping and justification break). The patch replaces
`mov al,X; cbw` with `movzx ax,X` of the same length (the game requires a 386
anyway). Glyph drawing itself (0598:0407) already treats characters as
unsigned.

2. Wider dialog topic buttons. Overlay 143 lays out the topic buttons in a grid
of 4 (records of 33 bytes, as in REQ_*.DAT: x at +0Bh, width at +0Fh): x =
12 + 75 * column, width 70, the GoodBye button at x = 237. The patch stretches
the grid over the screen: x = 3 + 78 * column (3, 81, 159, 237), width 76, the
right edge 312 (the screen border is at 317); GoodBye stays at x = 237.
"""

from pathlib import Path

from cyclopts import App

app = App(name="exe", help="Operations on KRONDOR.EXE")

EXE_SIZE = 454960

# file offset: (original bytes, patched bytes)
PATCHES: dict[int, tuple[bytes, bytes]] = {
    0x039654: (bytes.fromhex("8a0798"), bytes.fromhex("0fb607")),
    0x03974C: (bytes.fromhex("8a0798"), bytes.fromhex("0fb607")),
    0x03DF59: (bytes.fromhex("268a0798"), bytes.fromhex("260fb607")),
    0x03F718: (bytes.fromhex("8a460698"), bytes.fromhex("0fb64606")),
    0x03FAEE: (bytes.fromhex("268a0798"), bytes.fromhex("260fb607")),
    0x06E12A: (bytes.fromhex("8a46fe98"), bytes.fromhex("0fb646fe")),
    0x06E154: (bytes.fromhex("8a46fc98"), bytes.fromhex("0fb646fc")),
    0x06E402: (bytes.fromhex("8a46fe98"), bytes.fromhex("0fb646fe")),
    # dialog topic buttons (overlay 143)
    0x03D751: (bytes.fromhex("6bd24b"), bytes.fromhex("6bd24e")),  # imul dx, 75 -> 78
    0x03D754: (bytes.fromhex("83c20c"), bytes.fromhex("83c203")),  # add dx, 12 -> 3
    0x03D7BF: (bytes.fromhex("c7470f4600"), bytes.fromhex("c7470f4c00")),  # width 76
}
# the width of a topic button after the patch (baktt.keyword checks topics)
TOPIC_BUTTON_WIDTH = 76


@app.command(name="patch")
def patch_command(exe_path: Path) -> None:
    """Patch KRONDOR.EXE in place (running it again changes nothing)."""
    patch_exe(exe_path)


def patch_exe(exe_path: Path) -> int:
    """Return the number of applied changes; already patched places are skipped."""
    data = bytearray(exe_path.read_bytes())
    if len(data) != EXE_SIZE:
        raise ValueError(f"{exe_path}: size {len(data)}, expected {EXE_SIZE} (v1.02)")
    applied = 0
    for offset, (old, new) in PATCHES.items():
        current = bytes(data[offset : offset + len(old)])
        if current == new:
            continue
        if current != old:
            raise ValueError(
                f"{exe_path}: 0x{offset:06X} is {current.hex()}, expected {old.hex()}"
            )
        data[offset : offset + len(new)] = new
        applied += 1
    exe_path.write_bytes(data)
    print(f"{exe_path}: applied {applied} of {len(PATCHES)} changes")
    return applied
