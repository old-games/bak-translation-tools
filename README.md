# Betrayal at Krondor Translation Tools

**Development moved to https://github.com/old-games/bak-translation-tools**

This project is a set of tools for manipulating the resources
of the Betrayal at Krondor video game to enable translation of the game to
different languages (it was created to make a Russian translation, but may
be used for other languages).

The project is not affiliated with the original authors of Betrayal at Krondor, not
the developers of the `xbak` port.

## Requirements

 * Python 3.10 or later
 * `poetry` for dependency management (see https://python-poetry.org/docs/)
 * Tcl/Tk for GUI tools (Font Editor) - on Windows it is bundled with Python
   * On MacOS you may need to install it with `brew install tcl-tk` and `brew install python-tk`
 * C++ compiler for building Python C extensions (on Windows you can install
   Visual Studio with Python support enabled, including the "Python native
   development tools" component)


## Installation

1. Run `poetry install` to install the dependencies.

## Command Line Tools

 - `poetry python -m baktt.resources` - extracts/archives resource files from/to `krondor.001` / `krondor.rmf`
 - `poetry python -m baktt.fonts` - Operations on the font files (.FNT)
 - `poetry python -m baktt.book` - Operations on the book files (.BOK)
 - `poetry python -m baktt.images` - Operations on the image files (.PAL, .SCX, .BMX)

Use `--help` flag to see the available options.

## The Font Editor

Run the font editor with `poetry python -m baktt.gui.font_editor`

## Building the Font Editor for Windows

1. Make sure you have all requirements installed and have the project set up (see above).
2. Install `PyInstaller`: `poetry run python -m pip install PyInstaller`
3. Build the executable file: `poetry run python -m PyInstaller --noconsole --onefile .\tools\src\baktt\gui\font_editor.py`
4. The `.exe` file is saved to `dist` folder.

## TODO/Status

 - [x] Extract/archive resource files
 - [ ] Font editor
   - [x] Compress Fonts
   - [x] GUI
     - [x] Basic Window
     - [x] Character Table
     - [x] Display Glyph
     - [x] Editor Area
     - [x] Save files
     - [ ] Font Demo Widget
 - [ ] Translatable text extractor / packer
   - [x] BOK-files (books)
     - [x] Extract text
     - [x] Pack text
   - [ ] DDX-files (dialogs)
     - [ ] Extract text
     - [ ] Pack text
 - [ ] Image Processing
   - [x] Extract images
     - [x] SCX
     - [x] BMX
   - [ ] Pack images
