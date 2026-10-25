# Betrayal at Krondor Translation Tools

**Development moved to <https://github.com/old-games/bak-translation-tools>**

This project is a set of tools for translating the Betrayal at Krondor video
game. It is made for the Russian translation: reading and rebuilding the game
resources, the EXE patches and the checks do not depend on the language, but
the encoding, word locks, money plurals and the notes for translators are
Russian (see [Other Languages](#other-languages)).

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

## Common Tasks

`just --list` shows them all; the installed game (1.02) is expected in `./game`,
pass another folder as `just game=/path/to/krondor <task>`.

* `just export-all [out] [format]` - export everything to translate (default: `./translation`, xlsx)
* `just patch-game` - build the translated game from the tables, fonts and images in `data/` -> `data/krondor-ru.zip`
* `just play` - build and run it in DOSBox-X (`DOSBOX=/path/to/dosbox just play` for another executable)
* `just extract` - extract the game resources to `data/extracted` for manual `export`/`import`
* `just font-editor`, `just lint`

## Command Line Tools

* `uv run baktt export-all <game dir> <out dir>` - Export everything to translate from an installed game (1.02): one table per kind of text (`--format xlsx` for the old-games.ru translation system, `csv` for tests; columns: original, translation, key, note - see `data/README.md`), DROPCAPS.csv, the images with text as PNG (`--all-images` for all), README with the rules
* `uv run baktt resources` - extracts/archives resource files from/to `krondor.001` / `krondor.rmf`
* `uv run baktt fonts` - Operations on the font files (.FNT)
* `uv run baktt book` - Operations on the book files (.BOK): texts, drop caps (`dropcaps-export`/`dropcaps-import`)
* `uv run baktt dialog` - Operations on the dialog files (.DDX): export texts to a table (`--locks`: word lock riddles and answers to a separate table, the wheels are generated on import), build translated files
* `uv run baktt objinfo` - Item names (OBJINFO.DAT): export to a table, import a translation
* `uv run baktt keyword` - Dialog topics, answer buttons and NPC names (KEYWORD.DAT)
* `uv run baktt mnames` - Combat names: monsters and party members (MNAMES.DAT)
* `uv run baktt party` - Party member names in STARTUP.GAM (substituted for @ in texts)
* `uv run baktt ui` - Buttons and labels (REQ_*.DAT, LBL_*.DAT used by the game)
* `uv run baktt misc` - Spell names and descriptions, town names on the map (SPELLS.DAT, SPELLDOC.DAT, INVSPELL.DAT, FMAP_TWN.DAT)
* `uv run baktt images` - Operations on the image files (.PAL, .SCX, .BMX): export to PNG (`text_images_to_png` - only the images with text), build from edited PNGs (`from_png`)
* `uv run baktt exe` - Patch `KRONDOR.EXE`: font characters 0x80+, endings right after `@` (hero names), wider dialog topic buttons
* `uv run baktt exe-text` - Texts in `KRONDOR.EXE` (in place; longer DGROUP strings are moved to an extended DGROUP)
* `uv run baktt patch-game` - Create a translated game archive (see `data/README.md`)

Use `--help` flag to see the available options.

## Russian Text Encoding

Cyrillic letters are stored at codes 0x80..0xC2 (see `src/baktt/encoding.py`),
Latin letters are kept, so Roman page numbers in books still work. The original
`KRONDOR.EXE` gives every character >= 0x80 zero width (word wrapping breaks),
so the game must be patched with `baktt exe patch` (`patch-game` does it
automatically). Supported version: 1.02.

Russian fonts must have Cyrillic glyphs at 0x80..0xC2 too; edit them with the
font editor (characters are labeled in this encoding).

## Other Languages

Everything that is specific to Russian, to change for another language:

* `src/baktt/encoding.py` - the character map (`CHARMAP`) and the typography
  replacements (`TYPOGRAPHY`). Free codes are 0x80..0xDF: 0xE0..0xFF are control
  codes of the game's text renderer. Keep a lowercase letter at its uppercase
  code + 0x20: `toupper`/`tolower` in `KRONDOR.EXE` just add/subtract 0x20.
  The font editor labels the characters with this map.
* Fonts in `data/fonts/` - glyphs at the codes of the map; `ALIEN.FNT` (the
  runes of the Moredhel chests) needs a rune for every letter of the alphabet.
* Word locks in `src/baktt/dialog.py` - the wheel letters (`WHEEL_LETTERS`)
  and the characters allowed in an answer (`check_wordlock`).
* Money plurals - `src/baktt/asm/money.asm` chooses one of three forms by the
  Russian rule (1, 21, 31... / 2-4, 22-24... / the rest), the forms are the
  `EXE:MONEY:*` rows. The same rule fits e.g. Serbian and Bosnian; any other
  language needs a change in the assembly code (in English or German 21 takes
  the plural, in Polish only 1 takes the singular). Without the `EXE:MONEY:*`
  rows the game keeps its English plurals ("s").
* Notes for translators - Russian strings in the `export` code of `book`,
  `dialog`, `objinfo`, `keyword`, `ui`, `mnames`, `misc`, `party` and `exe_text`
  (e.g. how to decline hero names after `@`).

The resource formats, the rebuilding of the files, moving EXE strings to the
extended DGROUP, the EXE patches, the width and length checks and the tables
of the translation system are the same for any language.

## The Font Editor

Run the font editor with `uv run baktt gui font-editor`

## Building the Font Editor for Windows

GitHub Actions builds it on every change of the editor or the fonts code: the `baktt-font-editor-windows` artifact of the "Font editor for Windows" workflow. To build it yourself:

1. Make sure you have all requirements installed and have the project set up (see above).
2. Install `PyInstaller`: `uv pip install PyInstaller --python .venv\Scripts\python.exe`
3. Build the executable file: `uv run python -m PyInstaller --noconsole --onefile --name baktt-font-editor .\packaging\font_editor.py`
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
* [x] Russian endings after `@` in hero names (KRONDOR.EXE patch)
* [ ] Image Processing
  * [x] Extract images
    * [x] SCX
    * [x] BMX
  * [x] Pack images (LZW, LZSS and RLE compression; `images from_png`)
