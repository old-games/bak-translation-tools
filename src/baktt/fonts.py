from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import bitstring
from cyclopts import App
from filebuffer import FileBuffer

from baktt.encoding import (
    INVERSE_CHARMAP,
    LAST_CODE,
    LEGACY_GAME_FONT_TABLE,
    TRANSLITERATION_TABLE,
)

app = App(name="fonts", help="Operations on the font files")


@app.command(name="display")
def display_command(font_path: Path) -> None:
    """Display the font."""
    display_font(font_path)


@app.command(name="copy")
def copy_command(src: Path, dest: Path) -> None:
    """Copy a font file."""
    copy_font(src, dest)


LEGACY_TABLES = {
    "book": TRANSLITERATION_TABLE,
    "game": LEGACY_GAME_FONT_TABLE,
    # PUZZLE.FNT: the GAME scheme plus Ё/ё at 0x24/0x26
    "puzzle": {**LEGACY_GAME_FONT_TABLE, "Ё": 0x24, "ё": 0x26},
}


def make_em_dash(font: Font) -> Glyph:
    """Em dash made from the font's hyphen: same thickness, 4 pixels longer."""
    hyphen = font.glyphs[ord("-") - font.first]
    ink = 0
    for row in hyphen.rows:
        ink |= row
    left = next(x for x in range(16) if ink & (0x8000 >> x))
    right = max(x for x in range(16) if ink & (0x8000 >> x))
    length = right - left + 1 + 4
    mask = ((1 << length) - 1) << (16 - left - length)
    rows = [mask if row else 0 for row in hyphen.rows]
    return Glyph(width=left + length + 1, rows=rows)


# characters missing both in the English and in the legacy Russian fonts
DRAWN = {"—": make_em_dash}


def make_yo(base: Glyph) -> Glyph:
    """Cyrillic small yo from small ie: two dots two rows above the top of the
    letter, over its second and last ink columns (as in the GAME font design
    on the board)."""
    ink_rows = [y for y, row in enumerate(base.rows) if row]
    ink = 0
    for row in base.rows:
        ink |= row
    columns = [x for x in range(16) if ink & (0x8000 >> x)]
    rows = list(base.rows)
    top = ink_rows[0] - 2
    if top >= 0:
        rows[top] |= (0x8000 >> (columns[0] + 1)) | (0x8000 >> columns[-1])
    return Glyph(width=base.width, rows=rows)


# letters missing in a legacy font: drawn from another letter, or a substitute
DRAWN_FROM = {"ё": ("е", make_yo)}

# temporary substitutes for letters missing in a legacy font
FALLBACKS = {"Ё": "Е"}


@app.command(name="migrate")
def migrate_command(
    english: Path, legacy: Path, dest: Path, table: str = "book"
) -> None:
    """Move Cyrillic glyphs of a legacy font (drawn over Latin) to codes 0x80+.

    Latin glyphs are taken from the original English font `english`, Cyrillic
    glyphs from `legacy` according to `table`: "book" is the current
    TRANSLITERATION_TABLE, "game" is the earlier scheme used by GAME.FNT,
    "puzzle" is the same plus Ё/ё (PUZZLE.FNT).
    """
    migrate_font(english, legacy, dest, LEGACY_TABLES[table])


def migrate_font(
    english: Path, legacy: Path, dest: Path, table: dict[str, int]
) -> None:
    en = Font.from_file(english)
    ru = Font.from_file(legacy)
    assert en.first == ru.first, (en.first, ru.first)
    assert en.height == ru.height, (en.height, ru.height)

    def ru_glyph(code: int) -> Glyph:
        return ru.glyphs[code - ru.first].copy()

    glyphs = [g.copy() for g in en.glyphs]
    question = en.glyphs[ord("?") - en.first]
    # fonts with first == 0 (PUZZLE, ALIEN) already have empty slots up to 0xFA
    while en.first + len(glyphs) <= LAST_CODE:
        glyphs.append(question.copy())
    for code in range(0x80, LAST_CODE + 1):
        char = INVERSE_CHARMAP[code]
        if char in DRAWN:
            glyph = DRAWN[char](en)
        elif char in table:
            glyph = ru_glyph(table[char])
        elif char in DRAWN_FROM:
            source, draw = DRAWN_FROM[char]
            print(f"  {char!r} is missing, drawn from {source!r}")
            glyph = draw(ru_glyph(table[source]))
        else:
            print(f"  {char!r} is missing, using {FALLBACKS[char]!r} for now")
            glyph = ru_glyph(table[FALLBACKS[char]])
        glyphs[code - en.first] = glyph

    font = Font(
        name=dest.name, height=en.height, first=en.first, glyphs=glyphs, skips=en.skips
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.to_file(dest)
    print(f"{dest}: {len(glyphs)} glyphs, 0x{en.first:02X}..0x{LAST_CODE:02X}")


def display_font(font_path: Path) -> None:
    font = Font.from_file(font_path)

    print(f"Name:\t{font.name}")
    print(f"Height:\t{font.height}")
    print(f"Number of characters:\t{len(font.glyphs)}")

    print("\n\n\n")

    for char, glyph in enumerate(font.glyphs, font.first):
        print(f"{char}/{chr(char)}")
        print("=" * glyph.width)
        for row in glyph.to_pixels():
            for pixel in row:
                print("X" if pixel else ".", end="")
            print("")
        print("=" * glyph.width)
        print("\n\n\n")


def copy_font(src: Path, dest: Path) -> None:
    font = Font.from_file(src)
    dest_dir = dest.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    font.to_file(dest)


@dataclass
class Glyph:
    width: int
    rows: list[int]

    def to_pixels(self) -> list[bitstring.BitArray]:
        pixels: list[bitstring.BitArray] = []
        for row in self.rows:
            pixels.append(bitstring.BitArray(uint=row, length=16)[: self.width])
        return pixels

    @classmethod
    def from_pixels(cls, pixels: list[bitstring.BitArray]) -> Glyph:
        width = len(pixels[0])
        suffix = bitstring.BitArray(uint=0, length=16 - width)
        pixels = [row + suffix for row in pixels]
        return cls(width=width, rows=[row.uint for row in pixels])

    def copy(self) -> Glyph:
        return Glyph(
            width=self.width,
            rows=list(self.rows),
        )


SMILING_FACE = Glyph.from_pixels(
    [
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b011111100"),
        bitstring.BitArray("0b100000010"),
        bitstring.BitArray("0b101001010"),
        bitstring.BitArray("0b100000010"),
        bitstring.BitArray("0b101111010"),
        bitstring.BitArray("0b100000010"),
        bitstring.BitArray("0b011111100"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
        bitstring.BitArray("0b000000000"),
    ]
)


@dataclass
class Font:
    name: str
    height: int
    first: int
    glyphs: list[Glyph]
    skips: list[bytes]

    @classmethod
    def from_file(cls, path: Path) -> Font:
        buf = FileBuffer.from_file(path)
        tag = buf.uint32LE()
        if tag != 0x3A544E46:
            raise ValueError(f"{path} is not a font file")

        _ = buf.uint32LE()  # size of the tagged content

        skips: list[bytes] = []
        skips.append(buf.read(2))
        height = buf.uint8()

        skips.append(buf.read(1))
        first = buf.uint8()
        num_chars = buf.uint8()

        skips.append(buf.read(2))

        if buf.uint8() != 1:
            raise ValueError(f"Compression error: {path}")

        glyphbuf_size = buf.uint32LE()
        glyphbuf = buf.decompressRLE(glyphbuf_size)

        if not buf.at_end():
            raise ValueError("Not all data is consumed")

        glyph_offsets: list[int] = [glyphbuf.uint16LE() for _ in range(num_chars)]
        glyph_widths: list[int] = [glyphbuf.uint8() for _ in range(num_chars)]

        glyph_data_start: int = glyphbuf.tell()
        glyphs: list[Glyph] = []

        for offset, width in zip(glyph_offsets, glyph_widths, strict=True):
            glyphbuf.seek(glyph_data_start + offset)
            rows = []
            for _ in range(height):
                row = glyphbuf.uint8() << 8
                if width > 8:
                    row += glyphbuf.uint8()
                rows.append(row)
            glyphs.append(
                Glyph(
                    width=width,
                    rows=rows,
                )
            )

        return cls(
            name=path.name,
            height=height,
            first=first,
            glyphs=glyphs,
            skips=skips,
        )

    def to_file(self, path: Path) -> None:
        num_chars = len(self.glyphs)
        glyph_sizes = [
            self.height * (1 if glyph.width <= 8 else 2) for glyph in self.glyphs
        ]
        glyph_data_length = sum(glyph_sizes)

        glyph_offsets = [0]
        for size in glyph_sizes[:-1]:
            glyph_offsets.append(glyph_offsets[-1] + size)

        glyph_widths = [g.width for g in self.glyphs]

        glyph_offsets_length = 2 * num_chars
        glyph_widths_length = 1 * num_chars
        uncompressed_size = (
            glyph_offsets_length + glyph_widths_length + glyph_data_length
        )
        glyphbuf_uncompressed = FileBuffer(uncompressed_size)
        for offset in glyph_offsets:
            glyphbuf_uncompressed.put_uint16LE(offset)
        for width in glyph_widths:
            glyphbuf_uncompressed.put_uint8(width)
        for glyph in self.glyphs:
            for row in glyph.rows:
                glyphbuf_uncompressed.put_uint8(row // 256)
                if glyph.width > 8:
                    glyphbuf_uncompressed.put_uint8(row % 256)

        compressed_size, glyphbuf_compressed = glyphbuf_uncompressed.compressRLE()

        buf = FileBuffer(
            4  # Tag
            + 4  # Tagged content size
            + 2  # Skip 2
            + 1  # Height
            + 1  # Skip 1
            + 1  # First char
            + 1  # Num Chars
            + 2  # Glyphbuf size - trimmed
            + 1  # Compression type (1)
            + 4  # Glyphbuf size
            + compressed_size
        )

        buf.put_uint32LE(0x3A544E46)

        buf.put_uint32LE(buf.size() - 8)  # size of the tagged content

        # Skip 2
        buf.write(self.skips[0])

        buf.put_uint8(self.height)

        # Skip 1
        buf.write(self.skips[1])

        buf.put_uint8(self.first)
        buf.put_uint8(num_chars)

        # Skip 2
        buf.put_uint16LE(uncompressed_size % 65536)

        buf.put_uint8(1)  # Compression type
        buf.put_uint32LE(uncompressed_size)  # Glyphbuf size

        buf.write(glyphbuf_compressed.read())

        buf.to_file(path)
