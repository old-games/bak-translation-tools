# Data Folder Structure

This folder contains translation source files used by the `baktt patch-game` command.

**Copyright Notice:** All files in this folder (except this README.md and the Russian fonts in `fonts/`) are git-ignored due to copyright protection.

## Translation tables

Every kind of text is a table `<NAME>.xlsx` or `<NAME>.csv` (`DDX`, `LOCKS`,
`BOK`, `EXE`, `UI`, `OBJINFO`, `KEYWORD`, `MNAMES`, `MISC`, `PARTY`; not both
formats for one name) in the layout of the old-games.ru translation system:

| Column | Content |
|---|---|
| A | original (English, as in the game) |
| B | translation (empty = keep the original) |
| C | key - where the text lives in the game (`DIAL_Z18:003422`, `C11.BOK:003`, `EXE:DS:0686`...) |
| D | note for translators (limits, what is substituted...) |

- `.xlsx` has no header row: tables exported from the translation system are
  put here as is, and `baktt export-all` makes them for the system.
- `.csv` (UTF-8) has the header row `original,translation,key,note`: for test
  strings and manual edits (`baktt export-all --format csv`).

Rows are matched by key; their order and missing rows (phrases deleted in the
translation system) do not matter. The original is checked against the game
files. The leading and trailing whitespace of a translation (the paragraph
tab of dialogs...) is made the same as in the original.

### `BOK`

Book paragraphs (`baktt book export`), key `<NAME>.BOK:<paragraph index>`. A
paragraph starts with `\i` (normal text) or `\I` (italics); a translation must
keep this mark.

Used by: BookPatcher

### `DDX`, `LOCKS`

Dialogs (`baktt dialog export`). Markup: `{F0}`..`{F4}` (style of the next
word), `{E1}text{/E1}` (styled text, the byte is repeated before every
character), `{XX}` (any other byte), `#Name#` at the start of a snippet is the
speaker label.

Word locks (chests opened by a word, 152 snippets of `DIAL_Z17`) are not in
`DDX`: they are in `LOCKS`, two rows per lock - the riddle
(`DIAL_Z17:<offset>:riddle`) and the answer (`...:answer`). The answer: capital
letters, digits and spaces, at most 11 characters (lowercase letters are made
capital). The letters on the wheels are generated on import: every wheel gets
the answer letter and random letters, as many rows as in the original; an
unchanged answer keeps the original wheels. An empty row keeps the original
riddle or answer.

Used by: DialogPatcher

### `EXE`

Texts of `KRONDOR.EXE` (`baktt exe-text export`). A translation that fits into
the original (see the note) is written in place; longer `EXE:DS:*` strings are
moved to the end of DGROUP and their references are rewritten. The fixed-size
fields (`EXE:2760:*` conditions, max 10 bytes, `EXE:276B:*` skills, max 14)
cannot grow. printf specifiers (`%d`, `%ld`, `%s`, `%Fs`, ...) must stay the
same and in the same order.

Money in texts ("5 sovereigns and 3 royals") is built by code with English
plurals. Fill the `EXE:MONEY:*` rows (the joiner and three forms of each
word: for 1/21/31..., for 2-4/22-24..., for 0/5-20/25-30...) to switch it
to Russian plurals; all seven rows are required.

Used by: `patch-game`

### `OBJINFO`, `KEYWORD`, `MNAMES`, `PARTY`, `UI`, `MISC`

Item names, keywords (dialog topics, answer buttons, NPC names), monster names
(substituted for @1 in the dialogs before a fight), party member names, UI
texts (buttons, labels), spells, town names and credits, exported with
`baktt objinfo|keyword|mnames|party|ui|misc export`. Party names are written to
`startup.gam` (at most 9 bytes each).

Used by: ItemNamePatcher, KeywordPatcher, CombatNamePatcher, UIPatcher,
MiscPatcher; PARTY is applied by `patch-game` directly.

### `images/`

Edited PNG files exported with `baktt images bmx_to_png` / `scx_to_png`
(names `NAME.BMX_<index>.png`, `NAME.SCX.png`, same size). Colors are mapped
to the image palette; colors missing in the palette are replaced with the
nearest ones (a warning shows how many pixels).

In `BOOK.BMX` (book drop caps and decorations) images may change size, and
new images may be added with the next index (`BOOK.BMX_19.png`, ...), e.g.
Cyrillic drop caps.

Used by: ImagePatcher

### `DROPCAPS.csv`

Drop caps of the books, exported with `baktt book dropcaps-export`: the
letter, its BOOK.BMX image and the size of the box the text flows around.
Fill `new_image` (and optionally `new_box_width`/`new_box_height`) to use a
new letter.

Used by: BookPatcher

### `fonts/`

The Russian fonts (`GAME.FNT`, `BOOK.FNT`, `PUZZLE.FNT`, `ALIEN.FNT`) with
Cyrillic at 0x80+ (see `src/baktt/encoding.py`). Unlike the rest of this
folder they are kept in git. Edit them with the font editor.

Used by: FontPatcher (copied into the game), and to check the width of button
labels, dialog topics and EXE labels on import (`GAME.FNT`)

### `modified/`

Folder containing modified game resource files:

- `*.BMX` - Modified bitmap image files (e.g., `PUZZLE.BMX`)
  - Used by: ImagePatcher
- `*.SCX` - Modified screen image files (e.g., `C11.SCX`)
  - Used by: ImagePatcher

## Notes

- This folder may contain other files and folders used by other baktt commands or manual workflows
- The `baktt patch` command only reads the files listed above and ignores everything else
