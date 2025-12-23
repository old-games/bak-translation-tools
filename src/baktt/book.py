from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from cyclopts import App
from filebuffer import FileBuffer

from baktt.csvtools import Section, load_sections, save_sections
from baktt.encoding import encode

app = App(name="book", help="Operations on the book files")


@app.command(name="display")
def display_command(book_path: Path) -> None:
    """Display the book."""
    display_book(book_path)


@app.command(name="copy")
def copy_command(src: Path, dest: Path) -> None:
    """Copy a book file."""
    copy_book(src, dest)


@app.command(name="export")
def export_command(bok_dir: Path, csv_path: Path) -> None:
    """Export book text into a CSV file."""
    export_csv(bok_dir, csv_path)


@app.command(name="import")
def import_command(bok_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    """Import book text from a CSV file into book files."""
    import_csv(bok_dir, imported_dir, csv_path)


def display_book(book_path: Path) -> None:
    print(book_path)

    book = Book.from_file(book_path)

    for page_num, page in enumerate(book.pages, 1):
        print(f"Page {page_num}")
        print("===========")
        for text_block in page.text_blocks:
            print(text_block.text)


def copy_book(src: Path, dest: Path) -> None:
    book = Book.from_file(src)
    dest_dir = dest.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    book.to_file(dest)
    print(f"{src} is copied to {dest}")


def export_csv(bok_dir: Path, csv_path: Path) -> None:
    assert bok_dir.is_dir()

    sections: list[Section] = []

    for filename in os.listdir(bok_dir):
        if not filename.endswith(".BOK"):
            continue
        book = Book.from_file(bok_dir / filename)

        section = Section(name=filename)

        for page in book.pages:
            for text in page.text_blocks:
                section.strings.append((text.text, ""))

        sections.append(section)

    save_sections(csv_path, sections)
    print(f"Books from {bok_dir} are exported to {csv_path}")


def import_csv(bok_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    assert bok_dir.is_dir()
    assert imported_dir.is_dir()

    sections = load_sections(csv_path)
    section_by_name = {s.name: s for s in sections}

    for filename in os.listdir(bok_dir):
        if not filename.endswith(".BOK"):
            continue
        book = Book.from_file(bok_dir / filename)

        section = section_by_name[filename]
        strings = dict(section.strings)
        for page in book.pages:
            for text_block in page.text_blocks:
                translated = strings.get(text_block.text)
                if translated:
                    text_block.text = encode(translated)

        book.to_file(imported_dir / filename)

    print(f"Books from {csv_path} are imported to {imported_dir}")


@dataclass
class ImageInfo:
    x_pos: int
    y_pos: int
    id: int
    flag: int

    @property
    def size(self) -> int:
        return 4 * 2

    def write(self, buf: FileBuffer) -> None:
        buf.put_uint16LE(self.x_pos)
        buf.put_uint16LE(self.y_pos)
        buf.put_uint16LE(self.id)
        buf.put_uint16LE(self.flag)

    @classmethod
    def from_buf(cls, buf: FileBuffer) -> ImageInfo:
        return ImageInfo(
            x_pos=buf.uint16LE(),
            y_pos=buf.uint16LE(),
            id=buf.uint16LE(),
            flag=buf.uint16LE(),
        )


ITALICS: dict[str, bytes] = {
    "\\I": bytes.fromhex("F400000000000000000500"),
    "\\i": bytes.fromhex("F400000000000000000100"),
}


@dataclass
class TextInfo:
    paragraph: bool
    skips: list[bytes]
    text: str = ""

    @property
    def size(self) -> int:
        # start of paragraph + skip + text size
        return 1 + 16 + len(self.bytes)

    @property
    def bytes(self) -> bytes:
        assert self.text.startswith("\\i") or self.text.startswith("\\I")
        byte_string = self.text.encode("ascii")
        for placeholder, replacement in ITALICS.items():
            byte_string = byte_string.replace(placeholder.encode("ascii"), replacement)
        return byte_string

    @bytes.setter
    def bytes(self, byte_string: bytes) -> None:
        for replacement, placeholder in ITALICS.items():
            byte_string = byte_string.replace(placeholder, replacement.encode("ascii"))
        assert b"\xf2" not in byte_string
        assert b"\xf3" not in byte_string
        self.text = byte_string.decode("ascii")

    def write(self, buf: FileBuffer) -> None:
        buf.put_uint8(0xF1)
        buf.write(self.skips[0])
        buf.write(self.bytes)


@dataclass
class PageData:
    x_pos: int
    y_pos: int
    width: int
    height: int
    number: int
    id: int
    prev_id: int
    next_id: int
    flag: int
    show_number: bool
    decorations: list[ImageInfo] = field(repr=False)
    first_letters: list[ImageInfo] = field(repr=False)
    text_blocks: list[TextInfo] = field(repr=False)
    skips: list[bytes] = field(repr=False)

    @property
    def size(self) -> int:
        return (
            2  # x_pos
            + 2  # y_pos
            + 2  # width
            + 2  # height
            + 2  # number
            + 2  # id
            + 2  # prev_id
            + 2  # skip
            + 2  # next_id
            + 2  # flag
            + 2  # num_decoration
            + 2  # num_first_letters
            + 2  # show_number
            + 30  # skip
            + sum(decoration.size for decoration in self.decorations)  # decorations
            + sum(letter.size for letter in self.first_letters)  # first_letters
            + sum(text.size for text in self.text_blocks)  # text_blocks
            + 1  # end of page
        )

    @classmethod
    def from_buf(cls, buf: FileBuffer) -> PageData:
        skips: list[bytes] = []
        x_pos = buf.uint16LE()
        y_pos = buf.uint16LE()
        width = buf.uint16LE()
        height = buf.uint16LE()
        number = buf.uint16LE()
        id = buf.uint16LE()
        prev_id = buf.uint16LE()
        skips.append(buf.read(2))  # Looks line another copy of next_id
        next_id = buf.uint16LE()
        flag = buf.uint16LE()
        num_decorations = buf.uint16LE()
        num_first_letters = buf.uint16LE()
        show_number = buf.uint16LE() > 0
        skips.append(buf.read(30))  # TODO: what is this?

        decorations: list[ImageInfo] = []
        for _ in range(num_decorations):
            decorations.append(ImageInfo.from_buf(buf))

        first_letters: list[ImageInfo] = []
        for _ in range(num_first_letters):
            first_letters.append(ImageInfo.from_buf(buf))

        return PageData(
            x_pos=x_pos,
            y_pos=y_pos,
            width=width,
            height=height,
            number=number,
            id=id,
            prev_id=prev_id,
            next_id=next_id,
            flag=flag,
            show_number=show_number,
            decorations=decorations,
            first_letters=first_letters,
            text_blocks=list(cls.read_paragraphs(buf)),
            skips=skips,
        )

    @classmethod
    def read_paragraphs(cls, buf: FileBuffer) -> Iterable[TextInfo]:
        control = buf.uint8()
        if control == 0xF0:
            return

        assert control == 0xF1, f"{control=:02X}"

        while True:
            text_block, control = cls.read_paragraph(buf)
            yield text_block
            if control == 0xF0:
                return

            assert control == 0xF1, f"{control=:02X}"

    @classmethod
    def read_paragraph(cls, buf: FileBuffer) -> tuple[TextInfo, int]:
        skips: list[bytes] = [buf.read(16)]

        bytes_buf = BytesIO()

        char = buf.read(1)
        while char not in (b"\xf1", b"\xf0"):
            bytes_buf.write(char)
            char = buf.read(1)

        bytes_buf.seek(0)
        paragraph = TextInfo(
            paragraph=True,
            skips=skips,
        )
        paragraph.bytes = bytes_buf.read()
        return paragraph, ord(char)

    def write(self, buf: FileBuffer, is_last: bool) -> None:
        buf.put_uint16LE(self.x_pos)
        buf.put_uint16LE(self.y_pos)
        buf.put_uint16LE(self.width)
        buf.put_uint16LE(self.height)
        buf.put_uint16LE(self.number)
        buf.put_uint16LE(self.id)
        buf.put_uint16LE(self.prev_id)
        if is_last:
            buf.put_uint16LE(65534)
            buf.put_uint16LE(65535)
        else:
            buf.put_uint16LE(self.next_id)
            buf.put_uint16LE(self.next_id)
        buf.put_uint16LE(self.flag)
        buf.put_uint16LE(len(self.decorations))
        buf.put_uint16LE(len(self.first_letters))
        buf.put_uint16LE(self.show_number)
        buf.write(self.skips[1])

        for decoration in self.decorations:
            decoration.write(buf)

        for first_letter in self.first_letters:
            first_letter.write(buf)

        for text_block in self.text_blocks:
            text_block.write(buf)

        # end of page
        buf.put_uint8(0xF0)


@dataclass
class Book:
    pages: list[PageData]

    @classmethod
    def from_file(cls, path: Path) -> Book:
        buf = FileBuffer.from_file(path)
        _ = buf.uint32LE()  # file size
        num_pages = buf.uint16LE()
        page_offsets = [buf.uint32LE() for _ in range(num_pages)]

        pages: list[PageData] = []

        for page_offset in page_offsets:
            buf.seek(4 + page_offset)
            pages.append(PageData.from_buf(buf))
        return cls(pages=pages)

    def add_page(
        self,
        x_pos: int,
        y_pos: int,
        width: int,
        height: int,
        flag: int,
        show_number: bool,
        decorations: list[ImageInfo],
        first_letters: list[ImageInfo],
        text_blocks: list[TextInfo],
        skips: list[bytes],
    ) -> None:
        last_page = self.pages[-1]
        self.pages.append(
            PageData(
                x_pos=x_pos,
                y_pos=y_pos,
                width=width,
                height=height,
                number=last_page.number + 1,
                id=last_page.id + 1,
                prev_id=last_page.id,
                next_id=65535,
                flag=flag,
                show_number=show_number,
                decorations=decorations,
                first_letters=first_letters,
                text_blocks=text_blocks,
                skips=skips,
            )
        )
        last_page.next_id = self.pages[-1].id
        last_page.skips[0] = last_page.next_id.to_bytes(2, "little", signed=False)

    def to_file(self, path: Path) -> None:
        file_size = sum(p.size for p in self.pages) + len(self.pages) * 4 + 2
        buf = FileBuffer(4 + file_size)
        buf.put_uint32LE(file_size)
        buf.put_uint16LE(len(self.pages))
        page_offsets: list[int] = [2 + len(self.pages) * 4]
        for page in self.pages[:-1]:
            page_offsets.append(page_offsets[-1] + page.size)
        for offset in page_offsets:
            buf.put_uint32LE(offset)
        for i, page in enumerate(self.pages, 1):
            is_last = i == len(self.pages)
            page.write(buf, is_last)

        buf.to_file(path)
