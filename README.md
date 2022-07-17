# Betrayal at Krondor Translation Tools

This project is the is a set of tools for manipulating the resources
of the Betrayal at Krondor video game to enable translation of the game to
different languages (it was created to make a Russian translation, but may
be used for other languages).

The project is not affiliated with the original authors of Betrayal at Krondor, not
the developers of the `xbak` port.

## Requirements

 * Python 3.9 or later
 * Tcl/Tk for GUI tools (Font Editor) - on Windows it is bundled with Python
 * C++ compiler for building Python C extensions (on Windows you can install
   Visual Studio with Python support enabled, including the "Python native
   development tools" component)


## Installation

1. (optional) Create and activate python virtualenv:

```
python3 -m virtualenv venv tools/venv
source ./tools/venv/bin/activate
```

2. Install the `filebuffer` library

```
pip3 install -e ./tools/lib/filebuffer
```

3. Install the main project

```
pip3 install -e ./tools
```

## Command Line Tools

 - `python3 -m baktt.resources` - extracts/archives resource files from/to `krondor.001` / `krondor.rmf`
 - `python3 -m baktt.fonts` - Operations on the font files (.FNT)
 - `python3 -m baktt.book` - Operations on the book files (.BOK)
 - `python3 -m baktt.images` - Operations on the image files (.PAL, .SCX, .BMX)

Use `--help` flag to see the available options.

## Building the Font Editor for Windows

1. Make sure you have all requirements installed and have the project set up (see above).
2. Install `PyInstaller`: `pip3 install PyInstaller`
3. Build the executable file: `python3 -m PyInstaller --noconsole --onefile .\tools\src\baktt\gui\font_editor.py`
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
