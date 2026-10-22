"""Export everything to translate from an installed game in one go."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp

from baktt import book, dialog, exe_text, keyword, misc, mnames, objinfo, party, ui
from baktt.images import all_bmx_to_png, all_scx_to_png
from baktt.resources import extract_resources

README = Path(__file__).resolve().parents[2] / "data" / "README.md"


def _find(game_dir: Path, name: str) -> Path:
    for path in game_dir.iterdir():
        if path.name.lower() == name.lower():
            return path
    raise FileNotFoundError(f"{name} not found in {game_dir}")


def export_all(game_dir: Path, out_dir: Path, images: bool = True) -> None:
    """Export all texts to translate (and the images) from an installed game.

    `game_dir` must contain KRONDOR.EXE, krondor.rmf, krondor.001 and
    startup.gam (version 1.02). Creates in `out_dir`: one CSV per kind of
    text (key, english, russian[, note]), DROPCAPS.csv, images/ with PNGs and
    README.md with the rules for translators.
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

        dialog.export_csv(extracted, out_dir / "DDX.csv")
        book.export_csv(extracted, out_dir / "BOK.csv")
        objinfo.export_command(extracted, out_dir / "OBJINFO.csv")
        keyword.export_command(extracted, out_dir / "KEYWORD.csv")
        mnames.export_command(extracted, out_dir / "MNAMES.csv")
        party.export_command(startup, out_dir / "PARTY.csv")
        ui.export_command(extracted, out_dir / "UI.csv")
        misc.export_command(extracted, out_dir / "MISC.csv")
        exe_text.export_command(exe, out_dir / "EXE.csv")
        book.dropcaps_export_command(extracted, out_dir / "DROPCAPS.csv")

        if images:
            print("Exporting images to PNG...")
            all_bmx_to_png(extracted, out_dir / "images")
            all_scx_to_png(extracted, out_dir / "images")
        if README.exists():
            shutil.copy(README, out_dir / "README.md")
    finally:
        shutil.rmtree(extracted, ignore_errors=True)
    print(f"Done: {out_dir}")
