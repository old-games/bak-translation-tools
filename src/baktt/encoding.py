"""Text encoding for the Russian translation.

Cyrillic letters are stored at codes 0x80..0xC2, ASCII (including Latin) is
kept as is. Codes 0xE0..0xFF are control codes for the game's text renderer,
so they cannot be used for glyphs. Characters >= 0x80 get a proper width only
with the patched KRONDOR.EXE (see `baktt.exe_patch`).
"""

CYRILLIC_UPPER = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
CYRILLIC_LOWER = "абвгдежзийклмнопрстуфхцчшщъыьэюя"

CHARMAP: dict[str, int] = {
    **{ch: 0x80 + i for i, ch in enumerate(CYRILLIC_UPPER)},
    **{ch: 0xA0 + i for i, ch in enumerate(CYRILLIC_LOWER)},
    "Ё": 0xC0,
    "ё": 0xC1,
    "—": 0xC2,
}
INVERSE_CHARMAP: dict[int, str] = {v: k for k, v in CHARMAP.items()}

# the last code that must be present in a font
LAST_CODE = max(CHARMAP.values())


# Typography that has no glyphs: replaced the same way as in the original
# English text.
TYPOGRAPHY = {
    "«": '"',
    "»": '"',
    "„": '"',
    "“": '"',
    "”": '"',
    "’": "'",
    "–": "-",
    "…": "...",
    "\u00a0": " ",
}


def encode(s: str) -> bytes:
    """Unicode -> game bytes. Accepts ASCII, CHARMAP and TYPOGRAPHY."""
    out = bytearray()
    for char in s:
        if char in TYPOGRAPHY:
            out.extend(TYPOGRAPHY[char].encode("ascii"))
            continue
        if char in CHARMAP:
            out.append(CHARMAP[char])
        elif ord(char) < 0x80:
            out.append(ord(char))
        else:
            raise ValueError(
                f"Cannot encode character: {char!r}, code point {ord(char)}. "
                f"Text: {s!r}"
            )
    return bytes(out)


def decode(b: bytes) -> str:
    """Game bytes -> Unicode. Bytes outside of the encoding are an error."""
    out = []
    for c in b:
        if c < 0x80:
            out.append(chr(c))
        elif c in INVERSE_CHARMAP:
            out.append(INVERSE_CHARMAP[c])
        else:
            raise ValueError(f"Cannot decode byte 0x{c:02X} in {b!r}")
    return "".join(out)
