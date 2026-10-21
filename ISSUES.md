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
- Existing Russian fonts are converted with `baktt fonts migrate`.
