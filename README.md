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

* `uv run baktt resources` - extracts/archives resource files from/to `krondor.001` / `krondor.rmf`
* `uv run baktt fonts` - Operations on the font files (.FNT)
* `uv run baktt book` - Operations on the book files (.BOK)
* `uv run baktt images` - Operations on the image files (.PAL, .SCX, .BMX)

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
  * [ ] DDX-files (dialogs)
    * [ ] Extract text
    * [ ] Pack text
* [ ] Image Processing
  * [x] Extract images
    * [x] SCX
    * [x] BMX
  * [ ] Pack images
