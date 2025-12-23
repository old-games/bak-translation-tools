import os
import shutil
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import mkdtemp
from typing import Optional

from baktt.resources import extract_resources, archive_resources
from baktt.book import import_csv


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
        return (data_dir / "BOK.csv").exists()

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Applying book translations from BOK.csv...")

        # Import directly into extracted_dir (patching in place)
        import_csv(extracted_dir, extracted_dir, data_dir / "BOK.csv")
        bok_files = list(extracted_dir.glob("*.BOK"))
        print(f"  ✓ Applied translations to {len(bok_files)} book files")


class FontPatcher(Patcher):
    @property
    def name(self) -> str:
        return "Font Files"

    def can_apply(self, data_dir: Path) -> bool:
        modified_dir = data_dir / "modified"
        if not modified_dir.exists():
            return False
        return len(list(modified_dir.glob("*.FNT"))) > 0

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Copying modified font files...")
        modified_dir = data_dir / "modified"
        font_files = list(modified_dir.glob("*.FNT"))
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
        if not modified_dir.exists():
            return False
        bmx_files = list(modified_dir.glob("*.BMX"))
        scx_files = list(modified_dir.glob("*.SCX"))
        return len(bmx_files) + len(scx_files) > 0

    def apply(self, extracted_dir: Path, data_dir: Path) -> None:
        print("  Copying modified image files...")
        modified_dir = data_dir / "modified"
        image_files = list(modified_dir.glob("*.BMX")) + list(
            modified_dir.glob("*.SCX")
        )
        for image_file in image_files:
            dest = extracted_dir / image_file.name
            shutil.copy2(image_file, dest)
            print(f"    - {image_file.name}")
        print(f"  ✓ Copied {len(image_files)} image files")


# Register all patchers
PATCHERS: list[Patcher] = [
    BookPatcher(),
    FontPatcher(),
    ImagePatcher(),
]


def _find_case_insensitive_entry(parent: Path, name: str) -> Optional[Path]:
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

        print("✓ Validated game structure")
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
            for root, dirs, files in os.walk(temp_extract):
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
