from io import StringIO

CyrillicText = str
ASCIIText = str

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


INVERSE_TRANSLITERATION_TABLE = {v: k for k, v in TRANSLITERATION_TABLE.items()}


def encode(s: CyrillicText) -> ASCIIText:
    buf = StringIO()
    for char in s:
        if char in TRANSLITERATION_TABLE:
            encoded = chr(TRANSLITERATION_TABLE.get(char, ord(char)))
        else:
            if ord(char) > 127:
                raise ValueError(
                    f"Cannot encode character: {char!r}, code point {ord(char)}. "
                    f"Text: {s!r}"
                )
            encoded = char
        buf.write(encoded)
    buf.seek(0)
    return buf.read()
