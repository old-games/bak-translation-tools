from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import bitstring
from cyclopts import App
from filebuffer import FileBuffer

from baktt.encoding import INVERSE_CHARMAP

app = App(name="fonts", help="Operations on the font files")


@app.command(name="display")
def display_command(font_path: Path) -> None:
    """Display the font."""
    display_font(font_path)


@app.command(name="copy")
def copy_command(src: Path, dest: Path) -> None:
    """Copy a font file."""
    copy_font(src, dest)


@app.command(name="from-bdf")
def from_bdf_command(bdf: Path, base: Path, dest: Path) -> None:
    """Replace glyphs of the font BASE with the glyphs of a BDF font.

    The BDF is downloaded from the SP font bank."""
    font = Font.from_file(base)
    changed = apply_bdf(font, bdf)
    print(f"{bdf.name} -> {dest}: {len(changed)} glyphs changed")
    if changed:
        print("  " + " ".join(changed))
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.to_file(dest)


def game_char(code: int) -> str:
    """The character a game code stands for (see encoding.py)."""
    if code == 0x7F:
        return "\u2302"  # ⌂, as in the export for SP
    return chr(code) if code < 0x80 else INVERSE_CHARMAP.get(code, "")


def parse_bdf(path: Path) -> tuple[int, int, dict[int, tuple[int, list[int]]]]:
    """BDF -> (ascent, descent, {unicode: (advance, rows from the top of the cell)}).

    Rows are 16-bit with the leftmost pixel in bit 15, height = ascent + descent.
    """
    ascent = descent = None
    chars: dict[int, tuple[int, list[int]]] = {}
    lines = iter(path.read_text(encoding="utf-8").splitlines())
    for line in lines:
        key, _, value = line.partition(" ")
        if key == "FONT_ASCENT":
            ascent = int(value)
        elif key == "FONT_DESCENT":
            descent = int(value)
        elif key == "STARTCHAR":
            if ascent is None or descent is None:
                raise ValueError(f"{path}: no FONT_ASCENT/FONT_DESCENT before glyphs")
            enc = adv = bbx = None
            for line in lines:
                key, _, value = line.partition(" ")
                if key == "ENCODING":
                    enc = int(value.split()[0])
                elif key == "DWIDTH":
                    adv = int(value.split()[0])
                elif key == "BBX":
                    bbx = [int(v) for v in value.split()]
                elif key == "BITMAP":
                    break
            if enc is None or adv is None or bbx is None:
                raise ValueError(f"{path}: glyph without ENCODING/DWIDTH/BBX")
            w, h, xoff, yoff = bbx
            bitmap = []
            for line in lines:
                if line.startswith("ENDCHAR"):
                    break
                bitmap.append(int(line, 16) if line.strip() else 0)
            if len(bitmap) != h:
                raise ValueError(
                    f"{path}: U+{enc:04X} has {len(bitmap)} rows, BBX says {h}"
                )
            height = ascent + descent
            rows = [0] * height
            top = ascent - (h + yoff)
            nbits = ((w + 7) // 8) * 8
            where = f"{path}: U+{enc:04X} {chr(enc)!r}"
            for i, bits in enumerate(bitmap):
                bits &= ((1 << nbits) - 1) ^ ((1 << (nbits - w)) - 1)  # only BBX width
                if not bits:
                    continue
                y = top + i
                shift = 16 - nbits - xoff
                if not 0 <= y < height:
                    raise ValueError(f"{where}: pixels outside the cell height")
                if xoff < 0 or w + xoff > 16:
                    raise ValueError(f"{where}: pixels outside 16 px")
                rows[y] |= bits << shift if shift >= 0 else bits >> -shift
            chars[enc] = (adv, rows)
    if ascent is None or descent is None:
        raise ValueError(f"{path}: no FONT_ASCENT/FONT_DESCENT")
    return ascent, descent, chars


def apply_bdf(font: Font, bdf: Path) -> list[str]:
    """Put the BDF glyphs into the font at their game codes.

    Returns the changed characters."""
    ascent, descent, chars = parse_bdf(bdf)
    if ascent + descent != font.height:
        raise ValueError(
            f"{bdf}: height {ascent}+{descent}, the font {font.name} has {font.height}"
        )
    codes = {game_char(c): c for c in range(font.first, font.first + len(font.glyphs))}
    changed: list[str] = []
    errors: list[str] = []
    for u, (adv, rows) in chars.items():
        ch = chr(u)
        code = codes.get(ch)
        if code is None or ch == "":
            errors.append(f"U+{u:04X} {ch!r}: not in the game layout")
            continue
        if not 0 <= adv <= 16:
            errors.append(f"U+{u:04X} {ch!r}: width {adv} (max 16)")
            continue
        if any(row & ((1 << (16 - adv)) - 1) for row in rows):
            errors.append(f"U+{u:04X} {ch!r}: pixels to the right of the width {adv}")
            continue
        glyph = Glyph(width=adv, rows=rows)
        old = font.glyphs[code - font.first]
        if (old.width, old.rows) != (glyph.width, glyph.rows):
            font.glyphs[code - font.first] = glyph
            changed.append(ch)
    if errors:
        raise ValueError(f"{bdf.name}:\n  " + "\n  ".join(errors))
    return changed


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
