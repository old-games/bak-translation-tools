import os
import shutil
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import mkdtemp

from baktt.book import Book, dropcaps_import
from baktt.book import import_table as import_book_table
from baktt.book_layout import fix_books, image_sizes
from baktt.dialog import import_table as import_dialog_table
from baktt.exe_patch import patch_exe
from baktt.exe_text import import_table as import_exe_text_table
from baktt.fonts import Font
from baktt.images import images_from_png
from baktt.keyword import import_table as import_keyword_table
from baktt.misc import import_table as import_misc_table
from baktt.mnames import import_table as import_mnames_table
from baktt.objinfo import import_table as import_objinfo_table
from baktt.party import import_table as import_party_table
from baktt.resources import archive_resources, extract_resources
from baktt.table import find_table
from baktt.ui import import_table as import_ui_table

# the Russian fonts (*.FNT) in the data directory, kept in git
FONTS_DIR = "fonts"


class Patcher(ABC):
    @abstractmethod
    def can_apply(self, data_dir: Path) -> bool:
        """Check if this patcher can run (required files exist in data_dir)."""
        pass

    @abstractmethod
    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        """Apply the patch to extracted resources."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable patcher name for logging."""
        pass


class BookPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Book Translations"

    def can_apply(self, data_dir: Path) -> bool:
        return (
            find_table(data_dir, "BOK") is not None
            or (data_dir / "DROPCAPS.csv").exists()
        )

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        english = {p.name: Book.from_file(p) for p in extracted_dir.glob("*.BOK")}
        english_font = Font.from_file(extracted_dir / "BOOK.FNT")
        if find_table(data_dir, "BOK") is not None:
            print("  Applying book translations from BOK...")
            # Import directly into extracted_dir (patching in place)
            import_book_table(extracted_dir, extracted_dir, find_table(data_dir, "BOK"))
        if (data_dir / "DROPCAPS.csv").exists():
            print("  Applying drop caps from DROPCAPS.csv...")
            dropcaps_import(extracted_dir, extracted_dir, data_dir / "DROPCAPS.csv")
        # the ends of the books and the separators follow the translated text
        font_path = data_dir / FONTS_DIR / "BOOK.FNT"
        if not font_path.exists():
            font_path = extracted_dir / "BOOK.FNT"
        sizes = image_sizes(extracted_dir / "BOOK.BMX")
        font = Font.from_file(font_path)
        for message in fix_books(english, extracted_dir, english_font, font, sizes):
            print(f"  {message}")
        bok_files = list(extracted_dir.glob("*.BOK"))
        print(f"  ✓ Applied translations to {len(bok_files)} book files")


class DialogPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Dialog Translations"

    def can_apply(self, data_dir: Path) -> bool:
        return (
            find_table(data_dir, "DDX") is not None
            or find_table(data_dir, "LOCKS") is not None
        )

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        ddx, locks = find_table(data_dir, "DDX"), find_table(data_dir, "LOCKS")
        print("  Applying dialog translations from DDX/LOCKS...")
        import_dialog_table(extracted_dir, extracted_dir, ddx, locks)


class ItemNamePatcher(Patcher):
    @property
    def name(self) -> str:
        return "Item Names"

    def can_apply(self, data_dir: Path) -> bool:
        return find_table(data_dir, "OBJINFO") is not None

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying item names from OBJINFO...")
        font = data_dir / FONTS_DIR / "GAME.FNT"
        import_objinfo_table(
            extracted_dir,
            extracted_dir,
            find_table(data_dir, "OBJINFO"),
            font if font.exists() else None,
        )


class KeywordPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Keywords"

    def can_apply(self, data_dir: Path) -> bool:
        return find_table(data_dir, "KEYWORD") is not None

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying keywords from KEYWORD...")
        font = data_dir / FONTS_DIR / "GAME.FNT"
        import_keyword_table(
            extracted_dir,
            extracted_dir,
            find_table(data_dir, "KEYWORD"),
            font if font.exists() else None,
        )


class CombatNamePatcher(Patcher):
    @property
    def name(self) -> str:
        return "Combat Names"

    def can_apply(self, data_dir: Path) -> bool:
        return find_table(data_dir, "MNAMES") is not None

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying combat names from MNAMES...")
        import_mnames_table(
            extracted_dir, extracted_dir, find_table(data_dir, "MNAMES")
        )


class UIPatcher(Patcher):
    @property
    def name(self) -> str:
        return "UI Texts"

    def can_apply(self, data_dir: Path) -> bool:
        return find_table(data_dir, "UI") is not None

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying UI texts from UI...")
        # labels are measured with the Russian font, which is copied later
        font = data_dir / FONTS_DIR / "GAME.FNT"
        import_ui_table(
            extracted_dir,
            extracted_dir,
            find_table(data_dir, "UI"),
            font if font.exists() else None,
        )


class MiscPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Spells and Town Names"

    def can_apply(self, data_dir: Path) -> bool:
        return find_table(data_dir, "MISC") is not None

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying spells and town names from MISC...")
        import_misc_table(extracted_dir, extracted_dir, find_table(data_dir, "MISC"))


class FontPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Font Files"

    def can_apply(self, data_dir: Path) -> bool:
        return any((data_dir / FONTS_DIR).glob("*.FNT"))

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print(f"  Copying font files from {FONTS_DIR}/...")
        font_files = sorted((data_dir / FONTS_DIR).glob("*.FNT"))
        for font_file in font_files:
            dest = extracted_dir / font_file.name
            shutil.copy2(font_file, dest)
            print(f"    - {font_file.name}")
        print(f"  ✓ Copied {len(font_files)} font files")


class ImagePatcher(Patcher):
    @property
    def name(self) -> str:
        return "Image Files"

    def can_apply(self, data_dir: Path) -> bool:
        modified_dir = data_dir / "modified"
        return (
            any(modified_dir.glob("*.BMX"))
            or any(modified_dir.glob("*.SCX"))
            or any((data_dir / "images").glob("*.png"))
        )

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        images_dir = data_dir / "images"
        if images_dir.exists():
            print("  Building images from PNG files in images/...")
            images_from_png(extracted_dir, images_dir, extracted_dir)
        modified_dir = data_dir / "modified"
        if modified_dir.exists():
            image_files = list(modified_dir.glob("*.BMX")) + list(
                modified_dir.glob("*.SCX")
            )
            for image_file in image_files:
                shutil.copy2(image_file, extracted_dir / image_file.name)
                print(f"    - {image_file.name}")
            print(f"  ✓ Copied {len(image_files)} image files")


# Register all patchers
PATCHERS: list[Patcher] = [
    BookPatcher(),
    DialogPatcher(),
    ItemNamePatcher(),
    KeywordPatcher(),
    CombatNamePatcher(),
    UIPatcher(),
    MiscPatcher(),
    FontPatcher(),
    ImagePatcher(),
]


def _find_case_insensitive_entry(parent: Path, name: str) -> Path | None:
    """Return a child path whose name matches `name` ignoring case."""
    if not parent.exists():
        return None

    target = name.casefold()

    for child in parent.iterdir():
        if child.name.casefold() == target:
            return child

    return None


def _ensure_lowercase_entry(parent: Path, name: str) -> Path | None:
    """Ensure the specified entry exists and is renamed to the lowercase `name`."""

    entry = _find_case_insensitive_entry(parent, name)
    if entry is None:
        return

    desired_path = parent / name
    if entry != desired_path:
        entry.rename(desired_path)
        entry = desired_path

    return entry


def patch_game(
    input_zip: Path,
    output_zip: Path,
    data_dir: Path = Path("./data"),
) -> None:
    """Create a patched (translated) game archive from original game ZIP.

    Args:
        input_zip: Path to original game ZIP file (must contain krondor/ folder)
        output_zip: Path where patched game ZIP will be created
        data_dir: Path to translation data directory (default: ./data)
    """
    # Add data directory validation at the start
    if not data_dir.exists():
        print(f"Warning: Data directory not found at {data_dir}")
        print(f"Note: Translation data expected in {data_dir}")
        print()

    print("Starting game patching process...")
    print(f"Input: {input_zip}")
    print(f"Output: {output_zip}")
    print(f"Data directory: {data_dir}")
    print()

    # Initialize temp directory variables for cleanup
    temp_extract = None
    temp_resources = None
    temp_archived = None

    try:
        # Extract input ZIP
        print(f"Extracting input ZIP: {input_zip}...")
        temp_extract = Path(mkdtemp(prefix="bak_patch_extract_"))
        with zipfile.ZipFile(input_zip, "r") as zf:
            zf.extractall(temp_extract)

        # Normalize key resource names to lowercase for consistent processing
        krondor_dir = _ensure_lowercase_entry(temp_extract, "krondor")
        if krondor_dir is None or not krondor_dir.is_dir():
            raise ValueError("Invalid game ZIP: missing krondor/ folder")

        archive_path = _ensure_lowercase_entry(krondor_dir, "krondor.001")
        if archive_path is None:
            raise ValueError("Invalid game ZIP: missing krondor.001 in krondor/ folder")

        rmf_path = _ensure_lowercase_entry(krondor_dir, "krondor.rmf")
        if rmf_path is None:
            raise ValueError("Invalid game ZIP: missing krondor.rmf in krondor/ folder")

        exe_path = _find_case_insensitive_entry(krondor_dir, "krondor.exe")
        if exe_path is None:
            raise ValueError("Invalid game ZIP: missing krondor.exe in krondor/ folder")

        print("✓ Validated game structure")
        print()

        print("Patching KRONDOR.EXE (characters 0x80+)...")
        patch_exe(exe_path)
        if find_table(data_dir, "EXE") is not None:
            print("Applying EXE texts...")
            font = data_dir / FONTS_DIR / "GAME.FNT"
            import_exe_text_table(
                exe_path, find_table(data_dir, "EXE"), font if font.exists() else None
            )
        print()

        party_table = find_table(data_dir, "PARTY")
        if party_table is not None:
            startup_path = _find_case_insensitive_entry(krondor_dir, "startup.gam")
            if startup_path is None:
                raise ValueError("Invalid game ZIP: missing startup.gam")
            print("Applying party member names from PARTY...")
            import_party_table(startup_path, party_table)
            print()

        # Extract game resources
        temp_resources = Path(mkdtemp(prefix="bak_patch_resources_"))
        print("Extracting game resources from krondor.rmf...")
        extract_resources(rmf_path, temp_resources)
        print("✓ Extracted resources to temporary directory")
        print()

        # Apply translation patches
        print("Applying translation patches:")
        applied = 0
        skipped = 0

        for patcher in PATCHERS:
            if patcher.can_apply(data_dir):
                print(f"[{patcher.name}] Running...")
                patcher.apply(temp_resources, data_dir)
                applied += 1
            else:
                print(f"[{patcher.name}] Skipped (required data not found)")
                skipped += 1

        print()
        print(f"Applied {applied} patches, skipped {skipped}")
        print()

        # Rebuild game archives
        temp_archived = Path(mkdtemp(prefix="bak_patch_archived_"))
        resource_list = temp_resources / "_resources.csv"
        print("Rebuilding game archives...")
        archive_resources(resource_list, temp_archived)
        print("✓ Created patched krondor.001 and krondor.rmf")
        print()

        # Replace original files with patched versions
        print("Updating game files...")
        shutil.copy2(temp_archived / "krondor.001", archive_path)
        shutil.copy2(temp_archived / "krondor.rmf", rmf_path)
        print("✓ Replaced game archive files")
        print()

        # Create output ZIP with full original structure
        print(f"Creating output ZIP: {output_zip}...")
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(temp_extract):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_extract)
                    zf.write(file_path, arcname)
        print("✓ Created patched game archive")
        print()

    finally:
        # Cleanup temporary directories
        print("Cleaning up temporary directories...")
        if temp_extract and temp_extract.exists():
            shutil.rmtree(temp_extract, ignore_errors=True)
        if temp_resources and temp_resources.exists():
            shutil.rmtree(temp_resources, ignore_errors=True)
        if temp_archived and temp_archived.exists():
            shutil.rmtree(temp_archived, ignore_errors=True)
        print("✓ Cleanup complete")
        print()

    print("✓ Patching complete!")
