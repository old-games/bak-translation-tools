"""Russian drop caps of the books: chosen by the first letter of the translation.

The first paragraph of a book starts with a drop cap: a BOOK.BMX image on page 0,
and the text has no first letter (\\ilood soaked rags... = Blood). For the
translation the build looks at the first letter of the translated paragraph:

- the image of the letter is data/dropcaps/<letter>.png (e.g. Д.png), appended to
  BOOK.BMX; without one an original image of the same look is used
  (see LATIN); without both it is a translation error:
  the paragraph stays English with the English drop cap;
- the letter is removed from the text (translators write the whole word);
- the rectangle the text flows around (x1, y1, x2, y2) keeps its margins: x2, y2
  move by the difference of the image sizes. data/dropcaps/boxes.csv (book, x1,
  y1, x2, y2; empty = automatic) sets it by hand.

The images are 16-color with BOOK.PAL, color 0 is transparent; the width is padded
on the right to a multiple of 8, as in all the original images.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

from baktt import report
from baktt.book import ITALIC_MARKS, Book, _find_drop_cap, _paragraphs
from baktt.images import Image, TaggedBMXResource, image_palette

BOOK_BMX = "BOOK.BMX"
BOXES = "boxes.csv"
# Cyrillic letters drawn by an original drop cap (BOOK.BMX index)
LATIN = {"В": 0, "Р": 1, "А": 5, "Т": 6, "О": 15}
WIDTH_MULTIPLE = 8


@dataclass
class DropCap:
    book: str
    letter: str
    image: int
    box: tuple[int, int, int, int]


def load_images(src_dir: Path, dropcaps_dir: Path, dest_dir: Path) -> dict[str, int]:
    """Append data/dropcaps/<letter>.png to BOOK.BMX: {letter: image index}."""
    pngs: dict[str, Path] = {}
    for png in sorted(dropcaps_dir.glob("*.png")):
        letter = unicodedata.normalize("NFC", png.stem).upper()
        if len(letter) != 1 or not letter.isalpha():
            raise ValueError(f"{png}: the name must be one letter (Д.png)")
        if letter in pngs:
            raise ValueError(f"{png}: the same letter as {pngs[letter]}")
        pngs[letter] = png
    if not pngs:
        return {}
    bmx = TaggedBMXResource.from_file(src_dir / BOOK_BMX)
    letters = {}
    for letter, png in sorted(pngs.items()):
        index = len(bmx.images)
        # read as 8-bit (any width), 16 colors are checked here: the width is
        # padded to a multiple of 8 anyway
        empty = Image(width=0, height=0, flags=0, hires_locol=False, pixels=[])
        book_palette = image_palette(src_dir, BOOK_BMX, index)
        palette = replace(book_palette, colors=book_palette.colors[:16])
        image = Image.from_png(png, palette, empty, allow_resize=True)
        if max(image.pixels, default=0) > 15:
            raise ValueError(f"{png}: color index {max(image.pixels)} > 15")
        image.hires_locol = True
        image = _pad(image)
        bmx.images.append(image)
        letters[letter] = index
    dest_dir.mkdir(parents=True, exist_ok=True)
    bmx.to_file(dest_dir / BOOK_BMX)
    return letters


def _pad(image: Image) -> Image:
    """Pad the width with color 0 (transparent) on the right to a multiple of 8."""
    width = -(-image.width // WIDTH_MULTIPLE) * WIDTH_MULTIPLE
    if width == image.width:
        return image
    pixels = []
    for y in range(image.height):
        row = image.pixels[y * image.width : (y + 1) * image.width]
        pixels += row + [0] * (width - image.width)
    return Image(width, image.height, image.flags, image.hires_locol, pixels)


def load_boxes(path: Path) -> dict[str, list[int | None]]:
    """boxes.csv: book, x1, y1, x2, y2 (empty = automatic)."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {
            row["book"]: [
                int(row[k]) if (row.get(k) or "").strip() else None
                for k in ("x1", "y1", "x2", "y2")
            ]
            for row in csv.DictReader(f)
        }


def split_letter(text: str) -> tuple[str, str] | None:
    """(first letter, text without it) of a paragraph \\i...; spaces before the
    letter go too. None if there is no letter."""
    mark, rest = text[:2], text[2:].lstrip(" ")
    if mark not in ITALIC_MARKS or not rest or not rest[0].isalpha():
        return None
    return rest[0].upper(), mark + rest[1:]


def apply_dropcaps(
    english: dict[str, Book],
    books_dir: Path,
    src_dir: Path,
    dropcaps_dir: Path | None,
) -> list[DropCap]:
    """Set the drop caps of the translated books in books_dir (rewritten), BOOK.BMX
    with the new letters goes to books_dir too. src_dir has the original BOOK.BMX
    and BOOK.PAL."""
    letters: dict[str, int] = {}
    boxes: dict[str, list[int | None]] = {}
    if dropcaps_dir is not None and dropcaps_dir.is_dir():
        letters = load_images(src_dir, dropcaps_dir, books_dir)
        boxes = load_boxes(dropcaps_dir / BOXES)
    bmx_dir = books_dir if letters else src_dir
    bmx = TaggedBMXResource.from_file(bmx_dir / BOOK_BMX)
    sizes = [(i.width, i.height) for i in bmx.images]
    with_caps = set()
    done: list[DropCap] = []
    errors: list[str] = []
    for name, original in sorted(english.items()):
        page = next((p for p in original.pages if _find_drop_cap(p)), None)
        if page is None:
            continue
        index = original.pages.index(page)
        with_caps.add(name)
        book = Book.from_file(books_dir / name)
        box, cap = _find_drop_cap(book.pages[index])  # type: ignore[misc]
        text = book.pages[index].text_blocks[0]
        en_text = original.pages[index].text_blocks[0].text
        if text.text == en_text:
            continue  # not translated: the English drop cap stays
        first = original.pages[index].text_blocks[0]
        paragraph = next(i for i, t in enumerate(_paragraphs(original)) if t is first)
        key = f"{name}:{paragraph:03d}"
        found = split_letter(text.text)
        image = None
        if found is None:
            errors.append(f"{key}: the paragraph must start with a letter (drop cap)")
        else:
            image = letters.get(found[0], LATIN.get(found[0]))
            if image is None:
                errors.append(
                    f"{key}: no drop cap «{found[0]}» (data/dropcaps/{found[0]}.png)"
                )
        if found is None or image is None:
            text.text = en_text  # the English paragraph with the English drop cap
            book.to_file(books_dir / name)
            continue
        letter, text.text = found
        old_w, old_h = sizes[cap.id]
        new_w, new_h = sizes[image]
        auto = [box.x_pos, box.y_pos, box.id + new_w - old_w, box.flag + new_h - old_h]
        manual = boxes.pop(name, [None] * 4)
        x1, y1, x2, y2 = [
            a if m is None else m for a, m in zip(auto, manual, strict=True)
        ]
        box.x_pos, box.y_pos, box.id, box.flag = x1, y1, x2, y2
        cap.id = image
        book.to_file(books_dir / name)
        done.append(DropCap(name, letter, image, (x1, y1, x2, y2)))
        report.change(
            "Буквицы",
            f"{name}: «{letter}» — BOOK.BMX {image} ({new_w}x{new_h}), "
            f"обтекание {x1},{y1}–{x2},{y2}",
        )
    errors.extend(
        f"{BOXES}: {name}: no such book with a drop cap"
        for name in boxes
        if name not in with_caps
    )
    report.translation_errors(errors)
    return done
