#!/bin/env python3
import argparse
from dataclasses import dataclass
from pathlib import Path
import bitstring

from filebuffer import FileBuffer

parser = argparse.ArgumentParser(description="Operations on the font files")
subparsers = parser.add_subparsers(dest="command", required=True)

parser_display = subparsers.add_parser("display", help="Display the font")
parser_display.add_argument(
    "font_path", metavar="FONT_PATH", help="Path to .FNT file", type=Path
)

parser_copy = subparsers.add_parser("copy")
parser_copy.add_argument("src", metavar="SRC", help="Path to .FNT file", type=Path)
parser_copy.add_argument("dest", metavar="DEST", help="Path to .FNT file", type=Path)


def main() -> None:

    args = parser.parse_args()

    if args.command == "display":
        display_font(args.font_path)

    elif args.command == "copy":
        copy_font(args.src, args.dest)

    else:
        raise AssertionError()


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
    def from_pixels(cls, pixels: list[bitstring.BitArray]) -> "Glyph":
        width = len(pixels[0])
        suffix = bitstring.BitArray(uint=0, length=16 - width)
        pixels = [row + suffix for row in pixels]
        return cls(width=width, rows=[row.uint for row in pixels])

    def copy(self) -> "Glyph":
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
    def from_file(cls, path: Path) -> "Font":
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

        for offset, width in zip(glyph_offsets, glyph_widths):
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
        buf.write(self.skips.pop(0))

        buf.put_uint8(self.height)

        # Skip 1
        buf.write(self.skips.pop(0))

        buf.put_uint8(self.first)
        buf.put_uint8(num_chars)

        # Skip 2
        buf.put_uint16LE(uncompressed_size % 65536)
        # buf.write(self.skips.pop(0))

        buf.put_uint8(1)  # Compression type
        buf.put_uint32LE(uncompressed_size)  # Glyphbuf size

        buf.write(glyphbuf_compressed.read())

        buf.to_file(path)


if __name__ == "__main__":
    main()
