"""Images with text for the graphics translation of the translation system (SP).

SP keeps PNG only and checks a redraw of an indexed original byte by byte: the
same PLTE and the same transparency. So the originals are indexed PNG with the
palette the game draws the image with (PALETTES, IMAGE_PALETTES), color 0 of the
BMX sprites (cursors, buttons, titles) transparent, in folders by kind
(FOLDERS, the folder is the path inside the SP translation). File names stay
NAME.BMX_<n>.png / NAME.SCX.png: patch-game finds the images by the file name
in any subfolder of data/images and reads indexed PNG by index.

The drop caps of the books (BOOK.BMX) are not here: the Russian drop caps are
drawn from scratch.
"""

from __future__ import annotations

import csv
from pathlib import Path

from cyclopts import App
from openpyxl import Workbook
from PIL import Image as PILImage

from baktt.images import (
    TEXT_IMAGES,
    BMXResource,
    Image,
    Palette,
    SCXResource,
    TaggedBMXResource,
    image_palette,
)

app = App(name="sp-graphics", help="Images with text for the SP graphics translation")

# folder in SP by the game file
FOLDERS: dict[str, str] = {
    "POINTERG.BMX": "CURSORS",
    "BICONS1.BMX": "BUTTONS",
    "BICONS2.BMX": "BUTTONS",
    "CHAPTER.SCX": "CHAPTERS",
    "CHAPTER.BMX": "CHAPTERS",
    "INT_BOOK.BMX": "INTRO",
    "INT_BUNT.BMX": "INTRO",
    "INT_DYN.BMX": "INTRO",
    "INT_LGHT.BMX": "INTRO",
    "INT_TITL.BMX": "INTRO",
    "INT_MENU.SCX": "INTRO",
    "OPTIONS0.SCX": "MENU",
    "OPTIONS1.SCX": "MENU",
    "CONTENTS.SCX": "MENU",
    "CONT2.SCX": "MENU",
    "BLANK.SCX": "MENU",
    "CREDITS.SCX": "MENU",
    "COMPASS.BMX": "SCREENS",
    "INVMISC.BMX": "SCREENS",
    "INVSHP1.BMX": "SCREENS",
    "TELEPORT.BMX": "SCREENS",
    "C61D_MAC.BMX": "BOOKS",
}
SKIPPED = {"BOOK.BMX"}
HEADER = ["Файл", "Текст на изображении", "Перевод"]


def sp_path(file_name: str) -> str:
    """The path in SP of NAME.BMX_<n>.png / NAME.SCX.png."""
    name = (
        file_name.split(".png")[0].rsplit("_", 1)[0]
        if ".BMX_" in file_name
        else file_name[: -len(".png")]
    )
    return f"{FOLDERS[name]}/{file_name}"


def write_indexed(
    image: Image, palette: Palette, path: Path, transparent: bool
) -> None:
    """The image as an indexed PNG with the whole game palette (256 colors)."""
    img = PILImage.new("P", (image.width, image.height))
    flat = []
    for color in palette.colors:
        flat += [color.r, color.g, color.b]
    img.putpalette(flat + [0] * (768 - len(flat)))
    img.putdata(image.pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    if transparent:
        img.save(path, transparency=0)
    else:
        img.save(path)


def _bmx(src_dir: Path, name: str) -> BMXResource:
    path = src_dir / name
    return (
        TaggedBMXResource if TaggedBMXResource.is_tagged(path) else BMXResource
    ).from_file(path)


def originals(src_dir: Path) -> list[tuple[str, Image, Palette, bool]]:
    """(SP path, image, palette, transparent) of the images with text."""
    result = []
    for name, indexes in TEXT_IMAGES.items():
        if name in SKIPPED:
            continue
        if name.endswith(".SCX"):
            scx = SCXResource.from_file(src_dir / name)
            palette = Palette.get_by_name(src_dir, SCXResource.PALETTES[name])
            result.append((sp_path(f"{name}.png"), scx.image, palette, False))
            continue
        bmx = _bmx(src_dir, name)
        for index in indexes or range(len(bmx.images)):
            palette = image_palette(src_dir, name, index)
            result.append(
                (sp_path(f"{name}_{index}.png"), bmx.images[index], palette, True)
            )
    return result


def read_texts(path: Path | None) -> dict[str, tuple[str, str]]:
    """File name (without folder) -> (text on the image, translation) from a CSV
    file,text,translation (header row)."""
    if path is None:
        return {}
    with open(path, encoding="utf-8") as f:
        return {
            row["file"]: (row["text"], row.get("translation", ""))
            for row in csv.DictReader(f)
        }


@app.command(name="export")
def export_command(src_dir: Path, out_dir: Path, texts: Path | None = None) -> None:
    """Export the originals for the SP graphics translation: out_dir/originals
    (indexed PNG in the folders by kind, zip it for the upload) and
    out_dir/graphics.xlsx (Файл | Текст на изображении | Перевод).

    texts: a CSV file,text,translation with the text on the images (by file name).
    """
    known = read_texts(texts)
    rows = []
    for path, image, palette, transparent in originals(src_dir):
        write_indexed(image, palette, out_dir / "originals" / path, transparent)
        text, translation = known.get(Path(path).name, ("", ""))
        rows.append([path, text, translation])
    missing = [r[0] for r in rows if not r[1]]
    wb = Workbook()
    ws = wb.active
    ws.append(HEADER)
    for row in rows:
        ws.append(row)
    wb.save(out_dir / "graphics.xlsx")
    print(f"{len(rows)} images exported to {out_dir}")
    if missing:
        print(f"  no text for {len(missing)}: {', '.join(missing)}")


@app.command(name="redraws")
def redraws_command(src_dir: Path, png_dir: Path, out_dir: Path) -> None:
    """Convert edited PNGs (any subfolders, RGB or indexed) into SP redraws:
    indexed PNG with the palette of the original, in the folders by kind."""
    count = 0
    for png in sorted(png_dir.rglob("*.png")):
        file_name = png.name
        if ".BMX_" in file_name:
            name, _, index = file_name[: -len(".png")].rpartition("_")
            if name in SKIPPED or name not in FOLDERS:
                print(f"  skipped {png}: not an image of the SP translation")
                continue
            like = _bmx(src_dir, name).images[int(index)]
            palette = image_palette(src_dir, name, int(index))
            transparent = True
        elif file_name.endswith(".SCX.png"):
            name = file_name[: -len(".png")]
            like = SCXResource.from_file(src_dir / name).image
            palette = Palette.get_by_name(src_dir, SCXResource.PALETTES[name])
            transparent = False
        else:
            print(f"  skipped {png}")
            continue
        image = Image.from_png(png, palette, like, allow_resize=True)
        write_indexed(image, palette, out_dir / sp_path(file_name), transparent)
        count += 1
    print(f"{count} redraws written to {out_dir}")
