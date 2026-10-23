# Data Folder Structure

This folder contains translation source files used by the `baktt patch` command.

**Copyright Notice:** All files in this folder (except this README.md) are git-ignored due to copyright protection.

## Files and Folders Used by `baktt patch`

The `baktt patch` command looks for the following files. Each is optional - if present, the corresponding patcher will run:

### `BOK.csv`

Book translations in CSV format with two columns (original text, translated text). Sections are separated by `===FILENAME.BOK` headers.

Used by: BookPatcher

### `DDX.csv`, `LOCKS.csv`

Dialog translations exported with `baktt dialog export` (columns `key`,
`english`, `russian`). Rows with an empty `russian` column keep the original
text. Markup: `{F0}`..`{F4}` (style of the next word), `{E1}text{/E1}` (styled
text, the byte is repeated before every character), `{XX}` (any other byte),
`#Name#` at the start of a snippet is the speaker label.

Word locks (chests opened by a word, 152 snippets of `DIAL_Z17`) are not in
`DDX.csv`: they are in `LOCKS.csv`, two rows per lock - the riddle
(`DIAL_Z17:<offset>:riddle`) and the answer (`...:answer`). The answer: capital
letters, digits and spaces, at most 11 characters (lowercase letters are made
capital). The letters on the wheels are generated on import: every wheel gets
the answer letter and random letters, as many rows as in the original; an
unchanged answer keeps the original wheels. An empty row keeps the original
riddle or answer.

Used by: DialogPatcher

### `EXE.csv`

Texts of `KRONDOR.EXE` exported with `baktt exe-text export`. A translation
that fits into the original (the `note` column) is written in place; longer
`EXE:DS:*` strings are moved to the end of DGROUP and their references are
rewritten. The fixed-size fields (`EXE:2760:*` conditions, max 10 bytes,
`EXE:276B:*` skills, max 14) cannot grow. printf specifiers (`%d`, `%ld`,
`%s`, `%Fs`, ...) must stay the same and in the same order.

Money in texts ("5 sovereigns and 3 royals") is built by code with English
plurals. Fill the `EXE:MONEY:*` rows (the joiner and three forms of each
word: for 1/21/31..., for 2-4/22-24..., for 0/5-20/25-30...) to switch it
to Russian plurals; all seven rows are required.

Used by: `patch-game`

### `OBJINFO.csv`, `KEYWORD.csv`, `MNAMES.csv`, `PARTY.csv`, `UI.csv`, `MISC.csv`

Item names, keywords (dialog topics, answer buttons, NPC names), combat names,
party member names, UI texts (buttons, labels), spells and town names,
exported with `baktt objinfo|keyword|mnames|party|ui|misc export`. Same columns as `DDX.csv`.
Party names are written to `startup.gam` (at most 9 bytes each).

Used by: ItemNamePatcher, KeywordPatcher, CombatNamePatcher, UIPatcher,
MiscPatcher;
PARTY.csv is applied by `patch-game` directly.

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
