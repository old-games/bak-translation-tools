"""Page layout of the books (.BOK) as the game does it.

A port of the text layout of KRONDOR.EXE (overlay 147, file 0x3F410), used to
know where the text of a translated book ends: on which page and how low.

- The text of a page that has no text of its own continues the text left over
  by the previous page (the page whose "next" field points to it); the text that
  does not fit on the last page is lost.
- A paragraph (F1) carries 16 bytes of parameters: left and right margin,
  line height, extra space before the paragraph, first line indent, alignment.
- The first records of a page (as many as the field at +0x16) are rectangles
  (x1, y1, x2, y2, inclusive) the text flows around: the drop cap. The other
  records are images: they do not move the text.
- A line breaks after the last character before a space, or after '-', '.'
  (and line feeds) followed by a character that is not one of them.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from baktt.book import Book, ImageInfo, PageData
from baktt.fonts import Font
from baktt.images import TaggedBMXResource

PARAGRAPH = 0xF1
END = 0xF0
STYLE = 0xF4
F3 = 0xF3
SPACE = 0x20
MIN_SEGMENT = 15  # narrower free segments of a line are skipped


@dataclass
class Params:
    """Paragraph parameters (the 16 bytes after F1)."""

    left: int = 0
    right: int = 0
    line_height: int = 15
    space_before: int = 0
    indent: int = 0
    unused: int = 0
    space_before2: int = 0
    align: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> Params:
        return cls(*struct.unpack("<8h", data))


@dataclass
class Line:
    page: int  # index in book.pages
    x: int
    y: int
    width: int  # of the text (without justification)
    start: int  # offset in the text stream
    end: int  # inclusive
    avail: int  # width of the free segment
    justify: bool  # False for the last line of a paragraph
    text: bytes  # the text stream the offsets refer to
    paragraph: int  # number of the paragraph in the book
    first: bool  # the first line of the paragraph


@dataclass
class Layout:
    lines: list[Line] = field(default_factory=list)
    lost: bool = False  # text left over after the last page
    last_page: int | None = None  # the page where the text ends (the book closes)

    def bottom(self, page: int) -> int | None:
        """The lowest pixel row of the text on the page (glyph cell height 15)."""
        ys = [line.y for line in self.lines if line.page == page]
        return max(ys) + 15 - 1 if ys else None


def _signed(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value


def split_records(page: PageData) -> tuple[list[ImageInfo], list[ImageInfo]]:
    """(rectangles the text flows around, images) of a page.

    The file has two counts: images (+0x14) and rectangles (+0x16); book.py reads
    as many records as the first count into `decorations` and the rest into
    `first_letters`, but the rectangles come first.
    """
    records = page.decorations + page.first_letters
    rects = len(page.first_letters)
    return records[:rects], records[rects:]


def page_text(page: PageData) -> bytes:
    """The text of a page as stored in the file: F1 + parameters + text ..., F0."""
    return b"".join(
        bytes([PARAGRAPH]) + t.skips[0] + t.bytes for t in page.text_blocks
    ) + bytes([END])


class _Engine:
    def __init__(self, font: Font) -> None:
        self.font = font
        self.params = Params()
        self.x = 0  # S+1C current x
        self.y = 0  # S+1E line y
        self.seg_next = 0  # S+20 where the next free segment is looked for
        self.avail = 0  # S+22 width of the current segment
        self.used = 0  # S+24 width of the text up to the break
        self.end_of_text = False  # S+1A
        self.break_at = 0  # S+38
        self.justify = True  # S+26
        self.paragraph = -1  # paragraphs started so far, minus one
        self.first = False
        self.next_start = 0  # S+3C

    def width(self, c: int) -> int:
        index = c - self.font.first
        if 0 <= index < len(self.font.glyphs):
            return self.font.glyphs[index].width
        return 0

    def find_segment(self, page: PageData, rects: list[ImageInfo]) -> bool:
        """0x3F449: the next free segment of a line, from seg_next on."""
        left = page.x_pos + self.params.left
        right = page.x_pos + page.width - self.params.right
        x, y = self.seg_next, self.y
        y_end = y + self.params.line_height
        moved = True
        while moved:
            moved = False
            x = max(x, left)
            if x > right:
                x = left
                y += self.params.line_height
                y_end += self.params.line_height
                if page.y_pos + page.height - 1 <= y_end:
                    return False
            for r in rects:
                if _overlaps(r, y, y_end) and r.x_pos <= x <= r.id:
                    x = r.id + 1
                    moved = True
                    break
        width = right - x
        for r in rects:
            if _overlaps(r, y, y_end) and x < r.x_pos < x + width:
                width = r.x_pos - x
        self.x, self.y, self.avail = x, y, width
        self.seg_next = x + width + 1
        return True

    def start_line(self, page: PageData, rects: list[ImageInfo]) -> bool:
        while True:
            if not self.find_segment(page, rects):
                return False
            if self.avail >= MIN_SEGMENT:
                return True

    def measure_line(
        self, page: PageData, rects: list[ImageInfo], text: bytes, pos: int
    ) -> bool:
        """0x3F92F: the next line from pos; False if the page is full or the text
        has ended. Sets break_at (last character of the line) and next_start."""
        used = 0
        started = False
        self.break_at, self.used = pos, 0
        self.justify = True
        self.first = False
        p = pos
        while True:
            c = text[p]
            if c & 0xF0 == 0xF0:
                kind = c & 0x0F
                if kind == STYLE & 0x0F:
                    p += 11
                    continue
                if kind == F3 & 0x0F:
                    p += 3
                    continue
                if kind == PARAGRAPH & 0x0F:
                    if started:
                        self.break_at, self.used = p - 1, used
                        self.justify = False
                        break
                    if not self.start_line(page, rects):
                        return False
                    self.params = Params.from_bytes(text[p + 1 : p + 17])
                    self.seg_next = self.x = (
                        page.x_pos + self.params.left + self.params.indent
                    )
                    self.y += self.params.space_before + self.params.space_before2
                    p += 17
                    self.paragraph += 1
                    self.first = True
                    continue
                if kind == END & 0x0F:
                    self.end_of_text = True
                    if started:
                        self.break_at, self.used = p - 1, used
                        self.justify = False
                        break
                    return False
                raise ValueError(f"unknown code 0x{c:02X} at {p}")
            if not started:
                started = True
                if not self.start_line(page, rects):
                    return False
            used += self.width(c)
            if self.avail < used:
                break
            nxt = text[p + 1]
            if (nxt == SPACE and c != SPACE) or (_breakable(c) and not _breakable(nxt)):
                self.break_at, self.used = p, used
            if c == 0x0A:
                self.justify = False
            p += 1
        start = self.break_at + 1
        while text[start] == SPACE:
            start += 1
        self.next_start = start
        return True


def _overlaps(rect: ImageInfo, y: int, y_end: int) -> bool:
    """Whether a rectangle (x1, y1, x2, y2 in x_pos, y_pos, id, flag) is in the way
    of a line from y to y_end (the game checks only the two edges of the line)."""
    return rect.y_pos < y < rect.flag or rect.y_pos < y_end < rect.flag


def _breakable(c: int) -> bool:
    return c in (0x2D, 0x2E, 0x0A, 0x0D)


def layout_book(book: Book, font: Font) -> Layout:
    """Lay out the book page by page, following the text from page to page."""
    engine = _Engine(font)
    result = Layout()
    by_id = {page.id: i for i, page in enumerate(book.pages)}
    # text carried over to a page: (stream, position, parameters)
    carried: dict[int, tuple[bytes, int, Params]] = {}
    for index, page in enumerate(book.pages):
        rects, _images = split_records(page)
        engine.end_of_text = False
        engine.seg_next = engine.x = page.x_pos
        engine.y = page.y_pos
        if index in carried:
            text, pos, engine.params = carried.pop(index)
            engine.params = Params(**vars(engine.params))
        else:
            text, pos = page_text(page), 0
        while engine.measure_line(page, rects, text, pos):
            result.lines.append(
                Line(
                    index,
                    engine.x,
                    engine.y,
                    engine.used,
                    pos,
                    engine.break_at,
                    engine.avail,
                    engine.justify and engine.params.align == 3,
                    text,
                    engine.paragraph,
                    engine.first,
                )
            )
            pos = engine.next_start
            engine.x = engine.seg_next
        if engine.end_of_text:
            result.last_page = index
            break
        next_id = _signed(page.next_id)
        if next_id >= 0 and next_id in by_id:
            carried[by_id[next_id]] = (text, pos, Params(**vars(engine.params)))
        else:
            result.lost = True
            result.last_page = index
            break
    return result


def line_pixels(line: Line, font: Font) -> set[tuple[int, int]]:
    """The pixels of a line drawn as the game does (0x3F76D): justified lines get
    up to 10 extra pixels per space, the rest is spread between the letters."""
    engine = _Engine(font)
    chars: list[int] = []
    p = line.start
    while p <= line.end:
        c = line.text[p]
        if c == PARAGRAPH:
            p += 17
        elif c == STYLE:
            p += 11
        elif c == F3:
            p += 3
        else:
            chars.append(c)
            p += 1
    space_add, space_step = 0, 30000
    letter_add, letter_step = 0, 30000
    if line.justify:
        extra = line.avail - line.width
        spaces = chars.count(SPACE)
        letters = len(chars) - spaces
        if spaces:
            space_add, rem = divmod(extra, spaces)
            if rem:
                space_step = spaces * 50 // rem
        if space_add > 10 or not spaces:
            if space_add > 10:
                space_add, space_step = 10, 30000
            extra -= space_add * spaces
            letters -= 1
            if letters > 0:
                letter_add, rem = divmod(extra, letters)
                if rem:
                    letter_step = letters * 50 // rem
    space_count, letter_count = space_step, letter_step
    pixels: set[tuple[int, int]] = set()
    x = line.x
    for c in chars:
        index = c - font.first
        if 0 <= index < len(font.glyphs):
            glyph = font.glyphs[index]
            for row, bits in enumerate(glyph.rows):
                for col in range(16):
                    if bits & (0x8000 >> col):
                        pixels.add((x + col, line.y + row))
        x += engine.width(c)
        if line.justify:
            if c == SPACE:
                x += space_add
                space_count -= 50
                if space_count < 0:
                    x += 1
                    space_count = space_step
            else:
                x += letter_add
                letter_count -= 50
                if letter_count < 0:
                    x += 1
                    letter_count = letter_step
    return pixels


# --- the decoration at the end of a book --------------------------------------

END_IMAGE = 12  # the twig under the last line (BOOK.BMX)
SCREEN_BOTTOM = 350  # the book screen is 640x350; images must end above
GROUP_DY = 20  # images this close to the twig (by y) move with it (C94)
MIN_GAP = 4
NEW_PAGE = (40, 35, 554, 285)  # x, y, width, height of a continuation page


def ink_bottom(layout: Layout, page: int, font: Font, top: int) -> int:
    """The lowest row of the text pixels on a page (top - 1 if no text)."""
    rows = [
        y
        for line in layout.lines
        if line.page == page
        for _x, y in line_pixels(line, font)
    ]
    return max(rows) if rows else top - 1


def set_records(
    page: PageData, rects: list[ImageInfo], images: list[ImageInfo]
) -> None:
    """Store rectangles and images back (see split_records)."""
    records = rects + images
    page.decorations = records[: len(images)]
    page.first_letters = records[len(images) :]


def _end_group(page: PageData, bottom: int) -> list[int]:
    """Indices (in the page images) of the twig below the text and its neighbours."""
    _rects, images = split_records(page)
    twigs = [
        i
        for i, image in enumerate(images)
        if image.id == END_IMAGE and image.y_pos >= bottom - GROUP_DY
    ]
    if not twigs:
        return []
    twig = images[max(twigs, key=lambda i: images[i].y_pos)]
    return [
        i for i, image in enumerate(images) if abs(image.y_pos - twig.y_pos) <= GROUP_DY
    ]


def _add_page(book: Book, after: int) -> int:
    """A continuation page after book.pages[after] (the end of the text chain)."""
    last = book.pages[after]
    if last.text_blocks:
        x, y, width, height = NEW_PAGE
    else:
        x, y, width, height = last.x_pos, last.y_pos, last.width, last.height
    new_id = max(p.id for p in book.pages if p.id < 0xFFFE) + 1
    page = PageData(
        x_pos=x,
        y_pos=y,
        width=width,
        height=height,
        number=last.number + 1,
        id=new_id,
        prev_id=last.id,
        next_id=0xFFFF,
        flag=0,
        show_number=last.show_number,
        decorations=[],
        first_letters=[],
        text_blocks=[],
        skips=[(0xFFFE).to_bytes(2, "little"), bytes(30)],
    )
    last.next_id = new_id
    last.skips[0] = new_id.to_bytes(2, "little")
    book.pages.insert(after + 1, page)
    return after + 1


def fix_end(
    name: str,
    english: Book,
    book: Book,
    english_font: Font,
    font: Font,
    sizes: list[tuple[int, int]],
) -> list[str]:
    """Make the translated book end like the original: add pages if the text does
    not fit, put the twig under the last line (or remove it if it does not fit
    there). Returns what was changed."""
    messages: list[str] = []
    en_layout = layout_book(english, english_font)
    assert en_layout.last_page is not None
    en_last = en_layout.last_page
    en_page = english.pages[en_last]
    en_bottom = ink_bottom(en_layout, en_last, english_font, en_page.y_pos)
    group = _end_group(en_page, en_bottom)

    layout = layout_book(book, font)
    while layout.lost:
        assert layout.last_page is not None
        added = _add_page(book, layout.last_page)
        messages.append(f"{name}: text does not fit, page {added + 1} added")
        if added <= en_last:
            en_last += 1  # the original page moved down the list
        layout = layout_book(book, font)
    assert layout.last_page is not None
    last = layout.last_page
    # spare pages after the end of the original text have stray numbers (0, 469)
    for index in range(en_last + 1, last + 1):
        page, prev = book.pages[index], book.pages[index - 1]
        if page.number != prev.number + 1:
            messages.append(
                f"{name}: page {index + 1} number {page.number} -> {prev.number + 1}"
            )
            page.number = prev.number + 1
    bottom = ink_bottom(layout, last, font, book.pages[last].y_pos)
    if not group or (last == en_last and bottom <= en_bottom):
        return messages

    _rects, en_images = split_records(en_page)
    twig = max((en_images[i] for i in group), key=lambda image: image.y_pos)
    gap = max(twig.y_pos - en_bottom, MIN_GAP)
    delta = bottom + gap - twig.y_pos
    moved = [
        ImageInfo(image.x_pos, image.y_pos + delta, image.id, image.flag)
        for image in (en_images[i] for i in group)
    ]
    # take the twig off the original page and the pages after it
    for index in range(en_last, len(book.pages)):
        page = book.pages[index]
        rects, images = split_records(page)
        drop = set(group) if index == en_last else set(_end_group(page, page.y_pos))
        if drop:
            set_records(
                page, rects, [im for i, im in enumerate(images) if i not in drop]
            )
    where = f"page {last + 1}"
    if all(im.y_pos + sizes[im.id][1] <= SCREEN_BOTTOM for im in moved):
        rects, images = split_records(book.pages[last])
        set_records(book.pages[last], rects, images + moved)
        messages.append(
            f"{name}: end twig moved to {where}, y {twig.y_pos} -> {twig.y_pos + delta}"
        )
    else:
        messages.append(f"{name}: no room for the end twig under the text on {where}")
    return messages


def fix_separators(
    name: str,
    english: Book,
    book: Book,
    english_font: Font,
    font: Font,
    sizes: list[tuple[int, int]],
) -> list[str]:
    """Move the images that stand in a gap above a paragraph (the separators,
    BOOK.BMX 14: the paragraph has extra space before it) along with the first
    line of that paragraph, to the same distance above it."""
    messages: list[str] = []
    en_layout = layout_book(english, english_font)
    layout = layout_book(book, font)
    firsts = {line.paragraph: line for line in layout.lines if line.first}
    moves = []  # (page in english, image index, new page, new y)
    for index, page in enumerate(english.pages):
        _rects, images = split_records(page)
        lines = sorted(
            (line for line in en_layout.lines if line.page == index),
            key=lambda line: line.y,
        )
        for i, image in enumerate(images):
            if image.id == END_IMAGE or image.y_pos < page.y_pos:
                continue
            below = [line for line in lines if line.y >= image.y_pos]
            if not below or not below[0].first:
                continue
            anchor = below[0]
            if image.y_pos + sizes[image.id][1] > anchor.y:
                continue
            target = firsts.get(anchor.paragraph)
            if target is None:
                continue
            new_y = target.y + image.y_pos - anchor.y
            if (target.page, new_y) != (index, image.y_pos):
                moves.append((index, i, target.page, new_y))
    if not moves:
        return messages
    # the pages of the translation have the same indices up to the added ones;
    # the images are found by value (fix_end may have changed the lists)
    added: dict[int, list[ImageInfo]] = {}
    for index, i, new_page, new_y in moves:
        image = split_records(english.pages[index])[1][i]
        rects, images = split_records(book.pages[index])
        images.remove(image)
        set_records(book.pages[index], rects, images)
        added.setdefault(new_page, []).append(
            ImageInfo(image.x_pos, new_y, image.id, image.flag)
        )
        messages.append(
            f"{name}: separator moved from page {index + 1}, y {image.y_pos} "
            f"to page {new_page + 1}, y {new_y}"
        )
    for index, images in added.items():
        rects, old = split_records(book.pages[index])
        set_records(book.pages[index], rects, old + images)
    return messages


def text_overlaps(
    book: Book, layout: Layout, font: Font, sizes: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """(page, image index) of the images the text is drawn over."""
    found = []
    pixels: dict[int, set[tuple[int, int]]] = {}
    for line in layout.lines:
        pixels.setdefault(line.page, set()).update(line_pixels(line, font))
    for index, ink in pixels.items():
        _rects, images = split_records(book.pages[index])
        for i, image in enumerate(images):
            x2 = image.x_pos + sizes[image.id][0]
            y2 = image.y_pos + sizes[image.id][1]
            if any(image.x_pos <= x < x2 and image.y_pos <= y < y2 for x, y in ink):
                found.append((index, i))
    return found


def image_sizes(bmx_path: Path) -> list[tuple[int, int]]:
    """(width, height) of the BOOK.BMX images."""
    images = TaggedBMXResource.from_file(bmx_path).images
    return [(image.width, image.height) for image in images]


def fix_books(
    english: dict[str, Book],
    books_dir: Path,
    english_font: Font,
    font: Font,
    sizes: list[tuple[int, int]],
) -> list[str]:
    """fix_end for every translated book in books_dir (rewritten if changed), and
    warnings about images the translated text is drawn over (new ones)."""
    messages = []
    for name, original in sorted(english.items()):
        path = books_dir / name
        book = Book.from_file(path)
        changes = fix_end(name, original, book, english_font, font, sizes)
        changes += fix_separators(name, original, book, english_font, font, sizes)
        if changes:
            book.to_file(path)
            messages.extend(changes)
        en_layout = layout_book(original, english_font)
        old = set(text_overlaps(original, en_layout, english_font, sizes))
        for page, image in text_overlaps(book, layout_book(book, font), font, sizes):
            if (page, image) not in old:
                messages.append(
                    f"{name}: WARNING the text is drawn over an image, page {page + 1}"
                )
    return messages
