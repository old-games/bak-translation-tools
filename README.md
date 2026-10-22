# Betrayal at Krondor Translation Tools

**Development moved to <https://github.com/old-games/bak-translation-tools>**

This project is a set of tools for manipulating the resources
of the Betrayal at Krondor video game to enable translation of the game to
different languages (it was created to make a Russian translation, but may
be used for other languages).

The project is not affiliated with the original authors of Betrayal at Krondor, nor
the developers of the `xbak` port.

## Requirements

* Python 3.13 or later
* `uv` for dependency management (see <https://github.com/astral-sh/uv>)
* `just` for running common tasks (see <https://github.com/casey/just>) (optional but recommended)
* Tcl/Tk for GUI tools (Font Editor) - on Windows it is bundled with Python
  * On MacOS you may need to install it with `brew install tcl-tk` and `brew install python-tk`
* C++ compiler for building Python C extensions (on Windows you can install
   Visual Studio with Python support enabled, including the "Python native
   development tools" component)

## Installation

1. Create a virtual environment: `just venv` (or `uv venv --python 3.13`)
2. Install dependencies: `uv pip install -e . --python .venv/bin/python`
   * On Windows use `--python .venv\Scripts\python.exe`

## Command Line Tools

* `uv run baktt export-all <game dir> <out dir>` - Export everything to translate from an installed game (1.02): one CSV per kind of text, DROPCAPS.csv, images as PNG, README with the rules
* `uv run baktt resources` - extracts/archives resource files from/to `krondor.001` / `krondor.rmf`
* `uv run baktt fonts` - Operations on the font files (.FNT)
* `uv run baktt book` - Operations on the book files (.BOK): texts, drop caps (`dropcaps-export`/`dropcaps-import`)
* `uv run baktt dialog` - Operations on the dialog files (.DDX): export texts to CSV, build translated files
* `uv run baktt objinfo` - Item names (OBJINFO.DAT): export to CSV, import a translation
* `uv run baktt keyword` - Dialog topics, answer buttons and NPC names (KEYWORD.DAT)
* `uv run baktt mnames` - Combat names: monsters and party members (MNAMES.DAT)
* `uv run baktt party` - Party member names in STARTUP.GAM (substituted for @ in texts)
* `uv run baktt ui` - Buttons and labels (REQ_*.DAT, LBL_*.DAT used by the game)
* `uv run baktt misc` - Spell names and descriptions, town names on the map (SPELLS.DAT, SPELLDOC.DAT, INVSPELL.DAT, FMAP_TWN.DAT)
* `uv run baktt images` - Operations on the image files (.PAL, .SCX, .BMX): export to PNG, build from edited PNGs (`from_png`)
* `uv run baktt exe` - Patch `KRONDOR.EXE` so that font characters 0x80+ can be used
* `uv run baktt exe-text` - Texts in `KRONDOR.EXE` (in place; longer DGROUP strings are moved to an extended DGROUP)
* `uv run baktt patch-game` - Create a translated game archive (see `data/README.md`)

## Russian Text Encoding

Cyrillic letters are stored at codes 0x80..0xC2 (see `src/baktt/encoding.py`),
Latin letters are kept, so Roman page numbers in books still work. The original
`KRONDOR.EXE` gives every character >= 0x80 zero width (word wrapping breaks),
so the game must be patched with `baktt exe patch` (`patch-game` does it
automatically). Supported version: 1.02.

Fonts drawn with the previous scheme (Cyrillic over Latin glyphs) are converted
with `baktt fonts migrate`, which takes Latin glyphs from the original English
font and moves Cyrillic ones to 0x80+.

Use `--help` flag to see the available options.

## The Font Editor

Run the font editor with `uv run baktt gui font-editor`

## Building the Font Editor for Windows

1. Make sure you have all requirements installed and have the project set up (see above).
2. Install `PyInstaller`: `uv pip install PyInstaller --python .venv\Scripts\python.exe`
3. Build the executable file: `uv run python -m PyInstaller --noconsole --onefile .\src\baktt\gui\font_editor.py`
4. The `.exe` file is saved to `dist` folder.

## TODO/Status

* [x] Extract/archive resource files
* [ ] Font editor
  * [x] Compress Fonts
  * [x] GUI
    * [x] Basic Window
    * [x] Character Table
    * [x] Display Glyph
    * [x] Editor Area
    * [x] Save files
    * [ ] Font Demo Widget
* [ ] Translatable text extractor / packer
  * [x] BOK-files (books)
    * [x] Extract text
    * [x] Pack text
  * [x] DDX-files (dialogs)
    * [x] Extract text
    * [x] Pack text
  * [x] OBJINFO.DAT (item names; descriptions are dialogs in DIAL_Z18.DDX)
  * [x] KEYWORD.DAT (dialog topics, answer buttons, NPC names)
  * [x] REQ_*.DAT, LBL_*.DAT (buttons and labels)
  * [x] SPELLS.DAT, SPELLDOC.DAT, INVSPELL.DAT, FMAP_TWN.DAT
  * [x] CRED.DAT (credits)
  * [x] MNAMES.DAT (combat names)
  * [x] Party member names (STARTUP.GAM)
  * [x] Strings in KRONDOR.EXE in place
  * [x] Strings in KRONDOR.EXE longer than the original (DGROUP extension + reference relocation)
* [x] Characters 0x80+ in fonts (KRONDOR.EXE patch)
* [ ] Image Processing
  * [x] Extract images
    * [x] SCX
    * [x] BMX
  * [x] Pack images (LZW, LZSS and RLE compression; `images from_png`)
