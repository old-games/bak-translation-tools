#!/bin/env python3
import argparse
from dataclasses import dataclass
from pathlib import Path

from compression import decompressRLE
from filebuffer import FileBuffer

parser = argparse.ArgumentParser(description="Operations on the font files")
subparsers = parser.add_subparsers(dest="command", required=True)

parser_display = subparsers.add_parser("display", help="Display the font")
parser_display.add_argument(
    "font_path", metavar="FONT_PATH", help="Path to .FNT file", type=Path
)


def main() -> None:

    args = parser.parse_args()

    if args.command == "display":
        display_font(args.font_path)

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


@dataclass
class Glyph:

    width: int
    rows: list[int]

    def to_pixels(self) -> list[list[int]]:
        pixels: list[list[int]] = []
        bits = 16 if self.width > 8 else 8
        for row in self.rows:
            pixels.append([(row >> (bits - x - 1)) & 1 for x in range(self.width)])
        return pixels


@dataclass
class Font:

    name: str
    height: int
    first: int
    glyphs: list[Glyph]

    @classmethod
    def from_file(cls, path: Path) -> "Font":
        buf = FileBuffer.from_file(path)
        tag = buf.uint32LE()
        if tag != 0x3A544E46:
            raise ValueError(f"{path} is not a font file")

        _ = buf.uint32LE()  # size of the tagged content

        buf.skip(2)
        height = buf.uint8()

        buf.skip(1)
        first = buf.uint8()
        num_chars = buf.uint8()

        buf.skip(2)

        if buf.uint8() != 1:
            raise ValueError(f"Compression error: {path}")

        glyphbuf_size = buf.uint32LE()
        glyphbuf = decompressRLE(buf, glyphbuf_size)

        try:
            next(buf.io)
        except StopIteration:
            pass
        else:
            raise AssertionError("Not all data is consumed")

        glyph_offsets: list[int] = [glyphbuf.uint16LE() for _ in range(num_chars)]
        glyph_widths: list[int] = [glyphbuf.uint8() for _ in range(num_chars)]

        glyph_data_start: int = glyphbuf.tell()
        glyphs: list[Glyph] = []

        for offset, width in zip(glyph_offsets, glyph_widths):
            glyphbuf.seek(glyph_data_start + offset)
            rows = []
            for _ in range(height):
                row = glyphbuf.uint8()
                if width > 8:
                    row = row << 8
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
        )


if __name__ == "__main__":
    main()
