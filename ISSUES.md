# Issues

## Roman numerals in book pages block Cyrillic-only fonts

Problem:

- Book page numbers are rendered as Roman numerals (I, V, X). After replacing Latin glyphs with Cyrillic, those glyphs no longer exist in the font, so page numbers become unreadable.

Findings:

- In xbak, book page numbers are generated in code with a hardcoded Roman numeral table:
  - `xbak/src/Chapter.cc`: `ROMAN_NUMBER[]` used by `Chapter::ReadBook` with `pageNumberWidget.SetText(...)`.
- In the original DOS game, Roman numerals are also generated in code (not stored in resources):
  - `xbak/krondor/KRONDOR.EXE` contains a Roman conversion table at offset `0x2CABC`:
    - ASCII sequence `MDCLXVI`
    - 16-bit values `[1000, 500, 100, 50, 10, 5, 1]`
    - subtractor values `[100, 100, 10, 10, 1, 1, 0]`
- Roman numerals are not stored as plain strings in `krondor.001` or in `data/extracted`, so patching the resource archive alone will not affect page numerals.

Suggested fix paths:

- xbak: replace the Roman table with decimal formatting (e.g., `std::to_string(pd.number)`).
- Original game: patch the EXE to bypass the Roman conversion routine and format page numbers as decimal digits.

Alternatives:

- Add new glyphs for Roman numerals in the font file. This is the easiest workaround, but it means we'll have to
sacrifice some other glyphs (punctuation) to make space for them.

## Text rendering effectively limited to 128 glyphs

Problem:

- Fonts can store up to 256 glyphs, but the game only renders/uses the lower 128 character codes in practice.
- This blocks using native Cyrillic in addition to Latin and punctuation.

Findings:

- in `xbak`, character handling uses signed `char` in multiple text paths; bytes 0x80–0xFF become negative on common platforms.
- Negative values are treated as out of range in `DrawChar` and cause incorrect width calculations or skips.

Current workaround:

- Replace Latin glyphs with Cyrillic in the font.
- Drop some punctuation characters to make room for new glyphs.
