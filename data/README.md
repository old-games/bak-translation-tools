# Data Folder Structure

This folder contains translation source files used by the `baktt patch` command.

**Copyright Notice:** All files in this folder (except this README.md) are git-ignored due to copyright protection.

## Files and Folders Used by `baktt patch`

The `baktt patch` command looks for the following files. Each is optional - if present, the corresponding patcher will run:

### `BOK.csv`

Book translations in CSV format with two columns (original text, translated text). Sections are separated by `===FILENAME.BOK` headers.

Used by: BookPatcher

### `modified/`

Folder containing modified game resource files:

- `*.FNT` - Modified font files (e.g., `BOOK.FNT`, `GAME.FNT`)
  - Used by: FontPatcher
- `*.BMX` - Modified bitmap image files (e.g., `PUZZLE.BMX`)
  - Used by: ImagePatcher
- `*.SCX` - Modified screen image files (e.g., `C11.SCX`)
  - Used by: ImagePatcher

## Notes

- This folder may contain other files and folders used by other baktt commands or manual workflows
- The `baktt patch` command only reads the files listed above and ignores everything else
