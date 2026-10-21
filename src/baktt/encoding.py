"""Text encoding for the Russian translation.

Cyrillic letters are stored at codes 0x80..0xC2, ASCII (including Latin) is
kept as is. Codes 0xE0..0xFF are control codes for the game's text renderer,
so they cannot be used for glyphs. Characters >= 0x80 get a proper width only
with the patched KRONDOR.EXE (see `baktt.exe_patch`).

TRANSLITERATION_TABLE is the previous scheme (Cyrillic drawn over Latin
glyphs). The existing Russian fonts were drawn that way, so the table is only
needed to migrate them (`baktt fonts migrate`).
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


TRANSLITERATION_TABLE = {
    " ": 0x20,
    "!": 0x21,
    '"': 0x22,
    "ж": 0x23,
    "Ё": 0x24,
    "%": 0x25,
    "ё": 0x26,
    "и": 0x27,
    "(": 0x28,
    ")": 0x29,
    "*": 0x2A,
    "+": 0x2B,
    ",": 0x2C,
    "-": 0x2D,
    ".": 0x2E,
    "/": 0x2F,
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    ":": 0x3A,
    ";": 0x3B,
    "Ъ": 0x3C,
    "=": 0x3D,
    "ь": 0x3E,
    "?": 0x3F,
    "ю": 0x40,
    "а": 0x41,
    "б": 0x42,
    "ц": 0x43,
    "д": 0x44,
    "е": 0x45,
    "ф": 0x46,
    "г": 0x47,
    "х": 0x48,
    "I": 0x49,  # keep as is, it is used for roman numeral I
    "й": 0x4A,
    "к": 0x4B,
    "л": 0x4C,
    "м": 0x4D,
    "н": 0x4E,
    "о": 0x4F,
    "п": 0x50,
    "я": 0x51,
    "р": 0x52,
    "с": 0x53,
    "т": 0x54,
    "у": 0x55,
    "V": 0x56,  # keep as is, it is used for roman numeral V
    "в": 0x57,
    "X": 0x58,  # keep as is, it is used for roman numeral X
    "ы": 0x59,
    "з": 0x5A,
    "ш": 0x5B,
    "э": 0x5C,
    "щ": 0x5D,
    "ч": 0x5E,
    "ъ": 0x5F,
    "Ю": 0x60,
    "А": 0x61,
    "Б": 0x62,
    "Ц": 0x63,
    "Д": 0x64,
    "Е": 0x65,
    "Ф": 0x66,
    "Г": 0x67,
    "Х": 0x68,
    "И": 0x69,
    "Й": 0x6A,
    "К": 0x6B,
    "Л": 0x6C,
    "М": 0x6D,
    "Н": 0x6E,
    "О": 0x6F,
    "П": 0x70,
    "Я": 0x71,
    "Р": 0x72,
    "С": 0x73,
    "Т": 0x74,
    "У": 0x75,
    "Ж": 0x76,
    "В": 0x77,
    "Ь": 0x78,
    "Ы": 0x79,
    "З": 0x7A,
    "Ш": 0x7B,
    "Э": 0x7C,
    "Щ": 0x7D,
    "Ч": 0x7E,
}


# The Russian GAME.FNT was drawn with an earlier version of the scheme: soft
# signs are at 0x58/0x78, "zhe" at 0x56/0x76, and there is no "yo".
LEGACY_GAME_FONT_TABLE = {
    **dict(
        zip(
            CYRILLIC_LOWER,
            [
                0x41,
                0x42,
                0x57,
                0x47,
                0x44,
                0x45,
                0x56,
                0x5A,
                0x49,
                0x4A,
                0x4B,
                0x4C,
                0x4D,
                0x4E,
                0x4F,
                0x50,
                0x52,
                0x53,
                0x54,
                0x55,
                0x46,
                0x48,
                0x43,
                0x5E,
                0x5B,
                0x5D,
                0x5F,
                0x59,
                0x58,
                0x5C,
                0x40,
                0x51,
            ],
            strict=True,
        )
    ),
    **dict(
        zip(
            CYRILLIC_UPPER,
            [
                0x61,
                0x62,
                0x77,
                0x67,
                0x64,
                0x65,
                0x76,
                0x7A,
                0x69,
                0x6A,
                0x6B,
                0x6C,
                0x6D,
                0x6E,
                0x6F,
                0x70,
                0x72,
                0x73,
                0x74,
                0x75,
                0x66,
                0x68,
                0x63,
                0x7E,
                0x7B,
                0x7D,
                0x3C,
                0x79,
                0x78,
                0x7C,
                0x60,
                0x71,
            ],
            strict=True,
        )
    ),
}
