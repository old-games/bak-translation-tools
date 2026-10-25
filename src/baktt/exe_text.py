"""Texts in KRONDOR.EXE (v1.02): export to CSV and translation.

A translation that fits into the original string is written in place. A
longer DGROUP string is moved to a new area at the end of DGROUP: the load
image is extended in front of the stack segment (only SS in the MZ header and
the relocated stack entry of the Borland segment table change; the overlays
follow the image) and every reference to the string is rewritten. The
references (push/mov imm16 in the code, pointer words in DGROUP) were found by
disassembling all code and checked by hand, see REFS.

Money: mode 2 of the money formatting function builds English plurals
("%ld sovereigns and %ld royal" + "s"). When the EXE:MONEY:* rows are
translated, that branch jumps to asm/money.asm placed in the extended DGROUP,
which writes "<n> <form> <joiner> <m> <form>" with Russian plural forms
(1 / 2-4 / 5-20, 11-14).

- conditions (segment 2760): 7 records of 23 bytes, the name field is 11
  bytes (max 10), the rest of the record is data and is kept;
- skills (segment 276B): 16 records of 15 bytes (max 14);
- DGROUP (segment 29B5): the strings shown to the player, listed below with
  their offsets; printf format specifiers must stay the same and in order.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

from cyclopts import App

from baktt.encoding import decode, encode
from baktt.fonts import Font
from baktt.table import Row, load_translations, write_table
from baktt.ui import text_width

app = App(name="exe-text", help="Texts in KRONDOR.EXE (in place)")

HEADER_SIZE = 0x2400
DGROUP = 0x29B5

# segment: (record size, count, name field size)
ARRAYS = {
    0x2760: (23, 7, 11),  # conditions: Sick, Plagued, ...
    0x276B: (15, 16, 15),  # skills: Health, Stamina, ..., Stealth
}

# DGROUP offsets of the strings shown to the player (file names, config keys,
# debug output, resource tags and the English grammar suffixes "n ", "he",
# "ie", "s" are left out)
DGROUP_STRINGS = [
    0x00AA, 0x00DE, 0x03F6, 0x0604, 0x0686, 0x0751, 0x075E, 0x0772, 0x077D,
    0x0786, 0x07A3, 0x07BF, 0x07CB, 0x0AA2, 0x0AAF, 0x0ABA, 0x0B1C, 0x0B24,
    0x0B32, 0x0BFA, 0x0C0E, 0x0C52, 0x0C66, 0x0CA2, 0x0CDF, 0x0CE5, 0x0CE9,
    0x0D76, 0x0EEC, 0x0EF8, 0x0F0C, 0x0F17, 0x0F29, 0x0F78, 0x0F7E, 0x0F87,
    0x0F92, 0x0F9C, 0x101C, 0x1023, 0x1032, 0x1039, 0x1040, 0x1058, 0x1062,
    0x106E, 0x107A, 0x1084, 0x108D, 0x1096, 0x10A9, 0x10B1, 0x10BA, 0x10C4,
    0x10D0, 0x10D8, 0x10E1, 0x10F1, 0x10FE, 0x111B, 0x1120, 0x112B, 0x1135,
    0x113F, 0x114C, 0x1156, 0x1160, 0x1176, 0x119B, 0x11AA, 0x11B2, 0x11B6,
    0x11BC, 0x11C2, 0x11D7, 0x11E1, 0x11EC, 0x11F7, 0x1205, 0x1217, 0x1227,
    0x1230, 0x1237, 0x128F, 0x12A6, 0x12B7, 0x12BF, 0x12C8, 0x12CF, 0x136A,
    0x137A, 0x1386, 0x138E, 0x13A6, 0x13B2, 0x13BA, 0x13CD, 0x13D4, 0x13DA,
    0x13E1, 0x13EE, 0x13F3, 0x1441, 0x1449, 0x1452, 0x1459, 0x1463, 0x146B,
    0x1472, 0x1478, 0x16CC, 0x16E4, 0x16EF, 0x1C2E, 0x1CF5, 0x1D45, 0x1D54,
    0x1D5C,
]  # fmt: skip

# DGROUP string offset -> references: file offsets of the imm16 in the
# original EXE, or "DS:xxxx" for pointer words in DGROUP
REFS: dict[int, list[int | str]] = {
    0x00AA: [0x06CA6],
    0x00DE: [0x06CAF],
    0x03F6: ["DS:03E6"],
    0x0604: [0x33BAC],
    0x0686: [0x33CDB],
    0x0751: [0x350C2],
    0x075E: [0x350EC],
    0x0772: [0x350F5],
    0x077D: [0x350FE],
    0x0786: [0x35122],
    0x07A3: [0x3513F],
    0x07BF: [0x35148],
    0x07CB: [0x3517C],
    0x0AA2: [0x3B2CE],  # tavernkeeper (dialog variable 27)
    0x0AAF: [0x3B2D3],  # shopkeeper
    0x0ABA: [0x3B40A],
    0x0B1C: [0x3D7E9],
    0x0B24: [0x3D863],
    0x0B32: [0x3DC76],
    0x0BFA: [0x410FB],
    0x0C0E: [0x41116],
    0x0C52: [0x4134C],
    0x0C66: [0x41367],
    0x0CA2: [0x41831],
    0x0CDF: [0x41AB7],
    0x0CE5: [0x41AD1],
    0x0CE9: [0x41AEB],
    0x0D76: [0x4297A],
    0x0EEC: [0x49AD8],
    0x0EF8: [0x49B1E],
    0x0F0C: [0x49B34],
    0x0F17: [0x49B3D],
    0x0F29: [0x49CE7],
    0x0F78: [0x4B065],
    0x0F7E: [0x4B184],
    0x0F87: [0x4B1C9],
    0x0F92: [0x4B206],
    0x0F9C: [0x4B250],
    0x101C: [0x4D0B3],
    0x1023: [0x4D0C5],
    0x1032: [0x4D0E9],
    0x1039: [0x4D42D],
    0x1040: [0x4D448],
    0x1058: [0x4D4A1],
    0x1062: [0x4D4B3],
    0x106E: [0x4D4E2],
    0x107A: [0x4D518],
    0x1084: [0x4D52A],
    0x108D: [0x4D559],
    0x1096: [0x4D5A3],
    0x10A9: [0x4D5B8],
    0x10B1: [0x4D5BD],
    0x10BA: [0x4D5FE],
    0x10C4: [0x4D623],
    0x10D0: [0x4D613],
    0x10D8: [0x4D618],
    0x10E1: [0x4D64F],
    0x10F1: [0x4D6B8],
    0x10FE: [0x4D6BD],
    0x111B: [0x4D751],
    0x1120: [0x4D738],
    0x112B: [0x4D724],
    0x1135: [0x4D710],
    0x113F: [0x4D6FC],
    0x114C: [0x4D6E8],
    0x1156: [0x4D6D4],
    0x1160: [0x4D78B],
    0x1176: [0x4D7E2],
    0x119B: [0x4D829],
    0x11AA: [0x4D83E],
    0x11B2: [0x4D84D],
    0x11B6: [0x4D85C],
    0x11BC: [0x4D861],
    0x11C2: [0x4D8AC],
    0x11D7: [0x4D8A3],
    0x11E1: [0x4D8A8],
    0x11EC: [0x4DA12],
    0x11F7: [0x4DA33],
    0x1205: [0x4DA55],
    0x1217: [0x4DA6F],
    0x1227: [0x4DAB5],
    0x1230: [0x4DAE9],
    0x1237: [0x4DAF9],
    0x128F: [0x5194F],
    0x12A6: [0x5198D],
    0x12B7: [0x51A70],
    0x12BF: [0x51AAC],
    0x12C8: [0x51AE8],
    0x12CF: [0x51B29],
    0x136A: [0x54053],
    0x137A: [0x540CF],
    0x1386: [0x54144],
    0x138E: [0x54256],
    0x13A6: [0x54314],
    0x13B2: [0x5439B],
    0x13BA: [0x543E5],
    0x13CD: [0x544B2],
    0x13D4: [0x54510],
    0x13DA: [0x54535],
    0x13E1: [0x5462E],
    0x13EE: [0x54720],
    0x13F3: [0x5473E],
    0x1441: [0x57112],
    0x1449: [0x57137],
    0x1452: [0x5715C],
    0x1459: [0x57181],
    0x1463: [0x571B1],
    0x146B: [0x571D6],
    0x1472: [0x5720A],
    0x1478: [0x5722F],
    0x16CC: [0x5D195],
    0x16E4: [0x5D1BC],
    0x16EF: [0x5D24C],
    0x1C2E: [0x63E3F],
    0x1CF5: [0x643D6],
    0x1D45: ["DS:1D0A"],
    0x1D54: ["DS:1D0C"],
    0x1D5C: ["DS:1D0E"],
}  # fmt: skip

# asm/money.asm assembled with nasm (position independent, strings follow it)
MONEY_CODE = bytes.fromhex(
    "57e800005b83eb048cd88ec089f7668b46fc668b56f86685d274056685c07414"
    "6652b90100e81a00665a6685d2740e31c9e851006689d0b90400e8050030c0aa"
    "5fcb665051e85400b020aa5966586631d2665166b96400000066f7f1665989d0"
    "83f80b720583f80e761851b10af6f15980fc01741080fc02720880fc04770341"
    "eb0383c1028db7bd00e308ac84c075fb49ebf6ac84c07403aaebf8c366b90a00"
    "00006aff6631d266f7f180c230526685c075f15883f8ff7403aaebf7c3"
)
MONEY_KEYS = [
    ("EXE:MONEY:0", " and ", "joiner between sovereigns and royals"),
    ("EXE:MONEY:1", "sovereign", "form for 1, 21, 31..."),
    ("EXE:MONEY:2", "sovereigns", "form for 2-4, 22-24..."),
    ("EXE:MONEY:3", "sovereigns", "form for 0, 5-20, 25-30..."),
    ("EXE:MONEY:4", "royal", "form for 1, 21, 31..."),
    ("EXE:MONEY:5", "royals", "form for 2-4, 22-24..."),
    ("EXE:MONEY:6", "royals", "form for 0, 5-20, 25-30..."),
]
# overlay 130: mode 2 of the money function (file offset in the original EXE)
# and the code offset of its epilogue in the overlay. Overlay code offsets in
# the stubs are relative to the end of the 16-byte FBOV header.
MONEY_BRANCH = 0x3510B
MONEY_BRANCH_OLD = bytes.fromhex("66837ef80074566683")  # cmp dword [bp-8],0 / je ...
MONEY_EPILOGUE_IP = 0x0C47  # file 0x35187; overlay 130 code starts at 0x34540

FORMAT_SPEC = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[hlFN]*[a-zA-Z%]")


def grow_dgroup(data: bytes, size: int) -> tuple[bytearray, int]:
    """Insert `size` zero bytes (rounded to paragraphs) in front of the stack
    segment, i.e. at the end of DGROUP. Returns the new EXE and the DGROUP
    offset of the inserted area."""
    d = bytearray(data)
    last_page, pages, nrel, header_paras = struct.unpack_from("<4H", d, 2)
    ss, sp = struct.unpack_from("<2H", d, 0x0E)
    reloc_offset = struct.unpack_from("<H", d, 0x18)[0]
    header = header_paras * 16
    image_end = (pages - 1) * 512 + last_page if last_page else pages * 512
    if image_end != header + ss * 16 + sp or d[image_end : image_end + 4] != b"FBOV":
        raise ValueError("unexpected KRONDOR.EXE layout")
    paras = (size + 15) // 16
    area = (ss - DGROUP) * 16
    if area + paras * 16 > 0x10000:
        raise ValueError(f"DGROUP would exceed 64 KB ({area + paras * 16} bytes)")
    for i in range(nrel):
        offset, segment = struct.unpack_from("<HH", d, reloc_offset + 4 * i)
        linear = segment * 16 + offset
        (value,) = struct.unpack_from("<H", d, header + linear)
        if value >= ss:
            struct.pack_into("<H", d, header + linear, value + paras)
        if linear >= ss * 16:
            struct.pack_into("<H", d, reloc_offset + 4 * i + 2, segment + paras)
    insert_at = header + ss * 16
    d[insert_at:insert_at] = b"\0" * (paras * 16)
    new_end = image_end + paras * 16
    struct.pack_into("<HH", d, 2, new_end % 512, (new_end + 511) // 512)
    struct.pack_into("<H", d, 0x0E, ss + paras)
    return d, area


class Field:
    """A text field in the EXE: file offset, size (text + \\0 must fit)."""

    def __init__(self, key: str, offset: int, size: int, data: bytes) -> None:
        self.key = key
        self.offset = offset
        self.size = size
        self.text = data[offset : offset + size].split(b"\0")[0]


def fields(data: bytes) -> list[Field]:
    result = []
    for segment, (record_size, count, name_size) in ARRAYS.items():
        for i in range(count):
            offset = HEADER_SIZE + segment * 16 + record_size * i
            result.append(Field(f"EXE:{segment:04X}:{i:02d}", offset, name_size, data))
    for dgroup_offset in DGROUP_STRINGS:
        offset = HEADER_SIZE + DGROUP * 16 + dgroup_offset
        end = data.index(b"\0", offset)
        result.append(
            Field(f"EXE:DS:{dgroup_offset:04X}", offset, end - offset + 1, data)
        )
    return result


# --- notes for translators (column D of the table) ---------------------------

_MONEY_ALL = "Склонение включится, только если заполнены все 7 строк EXE:MONEY:0–6."
_MONEY_FORMS = ("1, 21, 31…", "2–4, 22–24…", "0, 5–20, 25–30…")
MONEY_NOTES = {
    "EXE:MONEY:0": "Соединитель между суммами sovereigns и royals "
    f"(«26 … and 9 …»). {_MONEY_ALL}",
    **{
        f"EXE:MONEY:{1 + i + 3 * j}": f"Слово «{word}» в форме для чисел {forms} "
        + _MONEY_ALL
        for j, word in enumerate(("sovereign", "royal"))
        for i, forms in enumerate(_MONEY_FORMS)
    },
}
# the strings replaced by the money plurals
MONEY_REPLACED = {"EXE:DS:0786", "EXE:DS:07A3", "EXE:DS:07BF", "EXE:DS:07CB"}
_KEEPER = (
    "Подставляется в реплики диалогов вместо @, всегда в одной форме — "
    "удобнее именительный падеж."
)
EXTRA_NOTES = {
    "EXE:DS:0F29": "Деньги на панели: число соверенов, буква, число роялов, буква. "
    "Склонения нет.",
    "EXE:DS:0CA2": "Число подставляется любое, склонения нет.",
    "EXE:DS:0AA2": _KEEPER,
    "EXE:DS:0AAF": _KEEPER,
}
# Screen width (pixels, GAME.FNT) of the labels whose place is set by the code:
# the ratings on the character screen (label at x=105, the numbers are aligned
# to the right at x=162; a two-digit number starts at x=154).
PIXEL_LIMITS = {
    "EXE:276B:00": 44,  # Health
    "EXE:276B:01": 44,  # Stamina
    "EXE:276B:02": 44,  # Speed
    "EXE:276B:03": 44,  # Strength
}
_PRINTF = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[lhF]*[a-zA-Z%]")


def field_note(field: Field, font: Font | None = None) -> str:
    size = field.size - 1
    if field.key.startswith("EXE:DS:"):
        parts = [
            f"На прежнем месте — до {size} знаков; длиннее тоже можно — "
            "место найдётся автоматически."
        ]
    else:
        parts = [f"Не длиннее {size} знаков: поле фиксированной длины."]
    codes = _PRINTF.findall(decode(field.text))
    if codes:
        parts.append(f"Коды {' '.join(codes)} сохранить в том же порядке.")
    if field.key in PIXEL_LIMITS:
        english = f" (английский — {text_width(font, field.text)} px)" if font else ""
        parts.append(f"Не шире {PIXEL_LIMITS[field.key]} px{english}.")
    if field.key in MONEY_REPLACED:
        parts.append(
            "Не используется, если заполнено склонение денег (строки EXE:MONEY:0–6)."
        )
    if field.key in EXTRA_NOTES:
        parts.append(EXTRA_NOTES[field.key])
    return " ".join(parts)


@app.command(name="export")
def export_command(exe_path: Path, table_path: Path, font: Path | None = None) -> None:
    """Export the texts to a table (.xlsx or .csv), with notes on the limits.

    `font` (GAME.FNT) is used to give the width of the English text in the
    notes of the labels with a width limit.
    """
    data = exe_path.read_bytes()
    game_font = Font.from_file(font) if font else None
    rows = [
        Row(field.key, decode(field.text), note=field_note(field, game_font))
        for field in fields(data)
    ]
    rows += [
        Row(key, english, note=MONEY_NOTES[key]) for key, english, _note in MONEY_KEYS
    ]
    write_table(table_path, rows)
    print(
        f"{len(fields(data))} EXE strings and {len(MONEY_KEYS)} money words "
        f"exported to {table_path}"
    )


@app.command(name="import")
def import_command(exe_path: Path, table_path: Path, font: Path | None = None) -> None:
    """Write the translation into KRONDOR.EXE in place.

    With `font` (the Russian GAME.FNT) the labels with a width limit are
    measured and must fit (PIXEL_LIMITS).
    """
    import_table(exe_path, table_path, font)


def import_table(exe_path: Path, table_path: Path, font: Path | None = None) -> None:
    data = bytes(exe_path.read_bytes())
    translations = load_translations(table_path)
    game_font = Font.from_file(font) if font else None
    errors: list[str] = []
    in_place: list[tuple[Field, bytes]] = []
    moved: list[tuple[Field, bytes]] = []
    for field in fields(data):
        if field.key not in translations:
            continue
        english, russian = translations[field.key]
        if english != decode(field.text):
            errors.append(f"{field.key}: english text does not match the EXE")
            continue
        if not russian.strip():
            continue
        if FORMAT_SPEC.findall(russian) != FORMAT_SPEC.findall(english):
            errors.append(
                f"{field.key}: format specifiers {FORMAT_SPEC.findall(russian)} "
                f"differ from {FORMAT_SPEC.findall(english)}"
            )
            continue
        try:
            encoded = encode(russian)
        except ValueError as e:
            errors.append(f"{field.key}: {e}")
            continue
        if game_font and field.key in PIXEL_LIMITS:
            width = text_width(game_font, encoded)
            if width > PIXEL_LIMITS[field.key]:
                errors.append(
                    f"{field.key}: {russian!r} is {width} px wide, "
                    f"max {PIXEL_LIMITS[field.key]} px"
                )
                continue
        if len(encoded) < field.size:
            in_place.append((field, encoded))
        elif field.key.startswith("EXE:DS:"):
            moved.append((field, encoded))
        else:
            errors.append(
                f"{field.key}: {russian!r} is {len(encoded)} bytes, "
                f"max {field.size - 1} (a fixed-size field)"
            )
    money = _money_words(translations, errors)
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")

    out = bytearray(data)
    for field, encoded in in_place:
        _write_in_place(out, field, encoded)
    if moved or money:
        out = _extend_dgroup(out, moved, money)
    exe_path.write_bytes(out)
    print(
        f"{len(in_place)} EXE strings written in place, "
        f"{len(moved)} moved to the end of DGROUP"
        + (", money plurals installed" if money else "")
        + f": {exe_path}"
    )


def _money_words(
    translations: dict[str, tuple[str, str]], errors: list[str]
) -> list[bytes] | None:
    """The 7 money words if they are translated (all or none)."""
    given = [translations.get(key, ("", ""))[1] for key, _, _ in MONEY_KEYS]
    if not any(word.strip() for word in given):
        return None
    words = []
    for (key, _, _), word in zip(MONEY_KEYS, given, strict=True):
        if not word.strip():
            errors.append(f"{key}: all EXE:MONEY:* rows must be translated")
            continue
        try:
            words.append(encode(word))
        except ValueError as e:
            errors.append(f"{key}: {e}")
    return words


def _write_in_place(data: bytearray, field: Field, encoded: bytes) -> None:
    start = field.offset
    old_end = start + len(field.text)
    # the text and its \0; the rest of the field (zeros or record data) stays
    data[start : start + len(encoded) + 1] = encoded + b"\0"
    if len(encoded) < len(field.text):
        data[start + len(encoded) + 1 : old_end + 1] = b"\0" * (
            old_end - start - len(encoded)
        )


def _extend_dgroup(
    data: bytearray, moved: list[tuple[Field, bytes]], money: list[bytes] | None
) -> bytearray:
    """Put the moved strings (and the money code) at the end of DGROUP and
    rewrite the references."""
    header = struct.unpack_from("<H", data, 8)[0] * 16
    insert_at = header + struct.unpack_from("<H", data, 0x0E)[0] * 16
    blob = b"".join(encoded + b"\0" for _, encoded in moved)
    money_offset = len(blob)
    if money:
        blob += MONEY_CODE + b"".join(word + b"\0" for word in money)
    out, area = grow_dgroup(data, len(blob))
    shift = len(out) - len(data)
    dgroup_file = header + DGROUP * 16
    out[dgroup_file + area : dgroup_file + area + len(blob)] = blob

    def file_offset(original: int) -> int:
        # code after the insertion point (overlays) moves with the image end
        return original + shift if original >= insert_at else original

    position = area
    for field, encoded in moved:
        old = int(field.key.split(":")[2], 16)
        for ref in REFS[old]:
            if isinstance(ref, str):  # a pointer word in DGROUP
                at = dgroup_file + int(ref.split(":")[1], 16)
            else:  # an imm16 in the code
                at = file_offset(ref)
            (value,) = struct.unpack_from("<H", out, at)
            if value != old:
                raise ValueError(f"{field.key}: reference at 0x{at:X} is 0x{value:X}")
            struct.pack_into("<H", out, at, position)
        position += len(encoded) + 1

    if money:
        at = file_offset(MONEY_BRANCH)
        if out[at : at + len(MONEY_BRANCH_OLD)] != MONEY_BRANCH_OLD:
            raise ValueError(f"unexpected code at the money branch 0x{at:X}")
        # push cs / push epilogue / push ds / push code / retf
        out[at : at + 9] = (
            b"\x0e\x68"
            + struct.pack("<H", MONEY_EPILOGUE_IP)
            + b"\x1e\x68"
            + struct.pack("<H", area + money_offset)
            + b"\xcb"
        )
    return out
