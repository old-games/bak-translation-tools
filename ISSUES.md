# Issues

## Resolved: text rendering effectively limited to 128 glyphs

Problem:

- Fonts can store up to 256 glyphs, but the game only rendered the lower 128 character codes correctly.
  The workaround was to draw Cyrillic over Latin glyphs, which broke Roman page numbers in books
  (I, V, X) and cost some punctuation.

Findings (KRONDOR.EXE 1.02):

- Codes 0xE0..0xFF are control codes of the text renderer (`Fx` - style of the next word,
  `Ex` - style of the next character), so they cannot be glyphs.
- Glyph drawing (resident segment 0598:0407, file offset 0x8187) treats the character as unsigned,
  so glyphs 0x80..0xDF are drawn fine.
- The width function (0598:06A6, file offset 0x8426) checks `0 <= c - first < count`, but all 8 of
  its call sites pass the character sign-extended with `cbw`. Characters >= 0x80 get zero width,
  so word wrapping and justification break (in German resources with the English EXE this looked
  like "several characters merging into one").
- xbak has the same problem because of signed `char`.

Fix:

- `baktt exe patch` replaces `mov al,X; cbw` with `movzx ax,X` at the 8 call sites (same length).
- Cyrillic is stored at 0x80..0xC2 (`src/baktt/encoding.py`), Latin glyphs stay, so Roman page
  numbers work again. Verified in DOSBox: dialogs, books (wrapping, justification, italics, page
  numbers) and the main menu.
- The Russian fonts were converted to this layout (Cyrillic at 0x80+).

## Resolved: Russian endings after `@` (hero names)

- The `@` substitution (overlay 142, file offset 0x3B49A) checks whether the character after `@`
  is a digit (`@N` = text variable N, otherwise `@` is the active hero's name) via the ctype table
  `[bx+3635h]`, but takes the character with `cbw`. For bytes >= 0x80 the index is negative, and
  the garbage before the table marks many Cyrillic letters as digits: `@у`, `@ом` printed a
  garbage variable and lost the letter (`@а`, `@е` worked).

Fix:

- `baktt exe patch` replaces `mov al,es:[bx+1]; cbw` with `movzx ax,byte es:[bx+1]` (file offset
  0x3B4A6, same length); the upper half of the table is zero. Verified in DOSBox: `@а`, `@е`,
  `@у`, `@ом` after Locklear, Owyn and Gorath.
- The export notes (DDX rows with `@`, PARTY) tell translators to decline names with endings.
