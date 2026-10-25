"""Export everything to translate from an installed game in one go."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Literal

from baktt import book, dialog, exe_text, keyword, misc, mnames, objinfo, party, ui
from baktt.images import all_bmx_to_png, all_scx_to_png, text_images_to_png
from baktt.resources import extract_resources

README = Path(__file__).resolve().parents[2] / "data" / "README.md"


def _find(game_dir: Path, name: str) -> Path:
    for path in game_dir.iterdir():
        if path.name.lower() == name.lower():
            return path
    raise FileNotFoundError(f"{name} not found in {game_dir}")


def export_all(
    game_dir: Path,
    out_dir: Path,
    images: bool = True,
    all_images: bool = False,
    format: Literal["xlsx", "csv"] = "xlsx",
) -> None:
    """Export all texts to translate (and the images) from an installed game.

    `game_dir` must contain KRONDOR.EXE, krondor.rmf, krondor.001 and
    startup.gam (version 1.02). Creates in `out_dir`: one table per kind of
    text (DDX, LOCKS, BOK, EXE, UI, ...; --format xlsx for the translation
    system, csv for tests), DROPCAPS.csv, images/ with PNGs of the images with
    text (all images with --all-images) and README.md with the rules for
    translators.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = _find(game_dir, "krondor.exe")
    rmf = _find(game_dir, "krondor.rmf")
    _find(game_dir, "krondor.001")
    startup = _find(game_dir, "startup.gam")

    extracted = Path(mkdtemp(prefix="baktt_export_"))
    try:
        print(f"Extracting resources from {rmf}...")
        extract_resources(rmf, extracted)

        def out(name: str) -> Path:
            return out_dir / f"{name}.{format}"

        dialog.export_table(extracted, out("DDX"), out("LOCKS"))
        book.export_table(extracted, out("BOK"))
        objinfo.export_command(extracted, out("OBJINFO"))
        keyword.export_command(extracted, out("KEYWORD"))
        mnames.export_command(extracted, out("MNAMES"))
        party.export_command(startup, out("PARTY"))
        ui.export_command(extracted, out("UI"))
        misc.export_command(extracted, out("MISC"))
        exe_text.export_command(exe, out("EXE"), extracted / "GAME.FNT")
        book.dropcaps_export_command(extracted, out_dir / "DROPCAPS.csv")

        if all_images:
            print("Exporting all images to PNG...")
            all_bmx_to_png(extracted, out_dir / "images")
            all_scx_to_png(extracted, out_dir / "images")
        elif images:
            text_images_to_png(extracted, out_dir / "images")
        if README.exists():
            shutil.copy(README, out_dir / "README.md")
    finally:
        shutil.rmtree(extracted, ignore_errors=True)
    print(f"Done: {out_dir}")
