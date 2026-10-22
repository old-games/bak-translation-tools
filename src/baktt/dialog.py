"""Dialogs (.DDX): text export to CSV and rebuilding with a translation.

DDX format (see also BaKGL, bak/dialog.cpp):
  u16 n; n x (u32 key, u32 snippet offset) - the index;
  then snippets, back to back:
    u8 style, u16 actor, u8, u8, u8 n_choices, u8 n_actions, u16 text length,
    n_choices x 10 bytes (u16 state, u16 min, u16 max, u32 target),
    n_actions x 10 bytes (u16 type, 8 bytes of parameters),
    text (non-empty text ends with \\0).
  Target: 0 - none; high nibble F - a dialog key (resolved through the index,
  possibly in another file); otherwise - a snippet offset in the same file.
  Action 0x10 (PushNextDialog) has the same kind of target at +2.

A translation changes text lengths, so the file is rebuilt: snippets keep their
order and all offsets (index, choice targets, action 0x10 targets) are
relocated.

Text markup in CSV:
  {F0}..{F4}        - bytes F0..F4 (style of the next word);
  {E1}text{/E1}     - byte E1 before every character of the text (same for E3...);
  {XX}              - any other byte that is not in the encoding;
  tabs and newlines are kept as is (a tab starts a paragraph).
"""

from __future__ import annotations

import csv
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cyclopts import App

from baktt.encoding import INVERSE_CHARMAP, encode

app = App(name="dialog", help="Operations on the dialog files (.DDX)")

HEADER_SIZE = 9
RECORD_SIZE = 10

# KRONDOR.EXE copies snippet text with expanded @N substitutions into a buffer
# of 0x3C8C bytes (allocated at file offset 0x33BF5) without bounds checking.
TEXT_BUFFER_SIZE = 0x3C8C
# room reserved for every @N substitution (a name or an amount of money)
SUBSTITUTION_SIZE = 40
KEY_MASK = 0xF0000000
PUSH_NEXT_DIALOG = 0x10
CSV_HEADER = ("key", "english", "russian")


@dataclass
class Snippet:
    header: bytes  # 9 bytes; the text length is recalculated on write
    choices: list[bytearray] = field(default_factory=list)
    actions: list[bytearray] = field(default_factory=list)
    text: bytes = b""  # without the trailing \0

    def records(self) -> list[bytearray]:
        return self.choices + self.actions

    def target_fields(self) -> list[tuple[int, int]]:
        """(index in records(), u32 position) of every jump target field."""
        fields = [(i, 6) for i in range(len(self.choices))]
        fields += [
            (len(self.choices) + i, 2)
            for i, a in enumerate(self.actions)
            if struct.unpack_from("<H", a, 0)[0] == PUSH_NEXT_DIALOG
        ]
        return fields

    def raw_text(self) -> bytes:
        return self.text + b"\0" if self.text else b""

    def size(self) -> int:
        return (
            HEADER_SIZE
            + RECORD_SIZE * (len(self.choices) + len(self.actions))
            + len(self.raw_text())
        )


@dataclass
class DialogFile:
    index: list[tuple[int, int]]  # (key, offset)
    snippets: dict[int, Snippet]  # offset -> snippet, in file order

    @classmethod
    def from_bytes(cls, data: bytes) -> DialogFile:
        (n,) = struct.unpack_from("<H", data, 0)
        index = [struct.unpack_from("<II", data, 2 + 8 * i) for i in range(n)]
        snippets: dict[int, Snippet] = {}
        p = 2 + 8 * n
        while p < len(data):
            start = p
            header = data[p : p + HEADER_SIZE]
            n_choices, n_actions = header[5], header[6]
            (length,) = struct.unpack_from("<H", header, 7)
            p += HEADER_SIZE
            choices = [
                bytearray(data[p + RECORD_SIZE * i : p + RECORD_SIZE * (i + 1)])
                for i in range(n_choices)
            ]
            p += RECORD_SIZE * n_choices
            actions = [
                bytearray(data[p + RECORD_SIZE * i : p + RECORD_SIZE * (i + 1)])
                for i in range(n_actions)
            ]
            p += RECORD_SIZE * n_actions
            text = data[p : p + length]
            p += length
            if text:
                if text[-1] != 0 or 0 in text[:-1]:
                    raise ValueError(f"unexpected text at 0x{start:X}: {text!r}")
                text = text[:-1]
            snippets[start] = Snippet(header, choices, actions, text)
        if p != len(data):
            raise ValueError("snippets overrun the end of file")
        dialog = cls(index=index, snippets=snippets)
        dialog._check_targets()
        return dialog

    @classmethod
    def from_file(cls, path: Path) -> DialogFile:
        return cls.from_bytes(path.read_bytes())

    def _check_targets(self) -> None:
        for _key, offset in self.index:
            if offset not in self.snippets:
                raise ValueError(f"index points to 0x{offset:X}: not a snippet")
        for start, snippet in self.snippets.items():
            records = snippet.records()
            for i, pos in snippet.target_fields():
                (target,) = struct.unpack_from("<I", records[i], pos)
                if target and not target & KEY_MASK and target not in self.snippets:
                    raise ValueError(
                        f"snippet 0x{start:X} points to 0x{target:X}: not a snippet"
                    )

    def to_bytes(self) -> bytes:
        new_offset: dict[int, int] = {}
        p = 2 + 8 * len(self.index)
        for start, snippet in self.snippets.items():
            new_offset[start] = p
            p += snippet.size()

        out = bytearray(struct.pack("<H", len(self.index)))
        for key, offset in self.index:
            out += struct.pack("<II", key, new_offset[offset])
        for snippet in self.snippets.values():
            raw_text = snippet.raw_text()
            if len(raw_text) > 0xFFFF:
                raise ValueError("snippet text is longer than 65535 bytes")
            out += snippet.header[:7] + struct.pack("<H", len(raw_text))
            for record in snippet.records():
                out += record
            out += raw_text
        return self._relocate(bytes(out), new_offset)

    def _relocate(self, data: bytes, new_offset: dict[int, int]) -> bytes:
        """Rewrite offset targets in the already assembled bytes."""
        out = bytearray(data)
        for start, snippet in self.snippets.items():
            records = snippet.records()
            for i, pos in snippet.target_fields():
                (target,) = struct.unpack_from("<I", records[i], pos)
                if target and not target & KEY_MASK:
                    at = new_offset[start] + HEADER_SIZE + RECORD_SIZE * i + pos
                    struct.pack_into("<I", out, at, new_offset[target])
        return bytes(out)


# --- word locks ---------------------------------------------------------------

# Word locks (chests opened by a word, BaKGL: "fairy chests") are snippets of
# DIAL_Z17.DDX: "ANSWER\n#\n<one row of wheel letters per line>\n#\n<riddle>".
# Each row is as long as the answer; column i of the rows holds the letters of
# wheel i, one of them is the answer letter. The letters are drawn with
# PUZZLE.FNT (or ALIEN.FNT for moredhel chests).
WORDLOCK_MAX_LENGTH = 11  # the longest answer in the original game


def parse_wordlock(text: str) -> tuple[str, list[str], str] | None:
    parts = text.split("\n#")
    if len(parts) != 3 or not parts[1].startswith("\n"):
        return None
    return parts[0], parts[1].split("\n")[1:], parts[2]


def check_wordlock(russian: str, english: str) -> list[str]:
    """Problems of a translated word lock (empty if it is fine)."""
    original = parse_wordlock(english)
    assert original is not None
    lock = parse_wordlock(russian)
    if lock is None:
        return ["word lock: expected ANSWER, #, wheel rows, #, riddle"]
    answer, rows, _riddle = lock
    problems = []
    if not answer:
        problems.append("word lock: empty answer")
    if len(answer) > WORDLOCK_MAX_LENGTH:
        problems.append(
            f"word lock: answer is {len(answer)} letters, max {WORDLOCK_MAX_LENGTH}"
        )
    if len(rows) != len(original[1]):
        problems.append(
            f"word lock: {len(rows)} wheel rows, the original has {len(original[1])}"
        )
    for row in rows:
        if len(row) != len(answer):
            problems.append(f"word lock: row {row!r} is not as long as {answer!r}")
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ0123456789 "
    )
    bad = sorted(set(answer + "".join(rows)) - allowed)
    if bad:
        problems.append(f"word lock: not capital letters/digits: {''.join(bad)!r}")
    if not problems:
        for i, letter in enumerate(answer):
            column = {row[i] for row in rows}
            if letter == " " and column != {" "}:
                problems.append(f"word lock: column {i + 1} must be spaces only")
            elif letter not in column:
                problems.append(
                    f"word lock: answer letter {letter!r} is not on wheel {i + 1}"
                )
    return problems


# --- text <-> markup -----------------------------------------------------------

_TAG = re.compile(r"\{(/?)([0-9A-F]{2})\}")


def text_to_markup(raw: bytes) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if 0xE0 <= c <= 0xEF and i + 1 < len(raw):
            # a run of "code + character" pairs with the same code
            run = []
            while i + 1 < len(raw) and raw[i] == c and raw[i + 1] < 0xE0:
                run.append(raw[i + 1])
                i += 2
            if run:
                out.append(f"{{{c:02X}}}{_plain(bytes(run))}{{/{c:02X}}}")
                continue
        out.append(_plain(raw[i : i + 1]))
        i += 1
    return "".join(out)


def _plain(raw: bytes) -> str:
    out = []
    for c in raw:
        if c < 0x80:
            out.append(chr(c))
        elif c in INVERSE_CHARMAP:
            out.append(INVERSE_CHARMAP[c])
        else:
            out.append(f"{{{c:02X}}}")
    return "".join(out)


def markup_to_text(s: str) -> bytes:
    out = bytearray()
    pos = 0
    run_code: int | None = None
    for m in _TAG.finditer(s):
        _append(out, s[pos : m.start()], run_code)
        closing, code = m.group(1) == "/", int(m.group(2), 16)
        if closing:
            if run_code != code:
                raise ValueError(f"unexpected {m.group(0)} in {s!r}")
            run_code = None
        elif 0xE0 <= code <= 0xEF and s.find(f"{{/{code:02X}}}", m.end()) >= 0:
            if run_code is not None:
                raise ValueError(f"nested {m.group(0)} in {s!r}")
            run_code = code
        else:
            out.append(code)
        pos = m.end()
    if run_code is not None:
        raise ValueError(f"unclosed {{{run_code:02X}}} in {s!r}")
    _append(out, s[pos:], run_code)
    return bytes(out)


def _append(out: bytearray, s: str, run_code: int | None) -> None:
    encoded = encode(s)
    if run_code is None:
        out += encoded
    else:
        for c in encoded:
            out += bytes((run_code, c))


# --- CSV ----------------------------------------------------------------------


def _dialog_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.DDX"))


def _key(path: Path, offset: int) -> str:
    return f"{path.stem}:{offset:06X}"


@app.command(name="export")
def export_command(ddx_dir: Path, csv_path: Path) -> None:
    """Export texts of all DDX files to CSV (key, english, russian)."""
    export_csv(ddx_dir, csv_path)


@app.command(name="import")
def import_command(ddx_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    """Build DDX files with the translation from CSV (empty = keep original)."""
    import_csv(ddx_dir, imported_dir, csv_path)


def export_csv(ddx_dir: Path, csv_path: Path) -> None:
    rows = 0
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for path in _dialog_files(ddx_dir):
            dialog = DialogFile.from_file(path)
            for offset, snippet in dialog.snippets.items():
                if snippet.text:
                    writer.writerow(
                        (_key(path, offset), text_to_markup(snippet.text), "")
                    )
                    rows += 1
    print(f"{rows} strings exported to {csv_path}")


def load_translations(csv_path: Path) -> dict[str, tuple[str, str]]:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        if tuple(header[:3]) != CSV_HEADER:
            raise ValueError(f"{csv_path}: expected header {CSV_HEADER}, got {header}")
        return {row[0]: (row[1], row[2]) for row in reader if row and row[0]}


def import_csv(ddx_dir: Path, imported_dir: Path, csv_path: Path) -> None:
    translations = load_translations(csv_path)
    imported_dir.mkdir(parents=True, exist_ok=True)
    used = 0
    errors: list[str] = []
    for path in _dialog_files(ddx_dir):
        dialog = DialogFile.from_file(path)
        for offset, snippet in dialog.snippets.items():
            key = _key(path, offset)
            if key not in translations:
                continue
            english, russian = translations[key]
            if english != text_to_markup(snippet.text):
                errors.append(f"{key}: english text does not match the game file")
                continue
            if not russian.strip():
                continue
            if parse_wordlock(english):
                problems = check_wordlock(russian, english)
                if problems:
                    errors.extend(f"{key}: {problem}" for problem in problems)
                    continue
            try:
                text = markup_to_text(russian)
            except ValueError as e:
                errors.append(f"{key}: {e}")
                continue
            size = len(text) + 1 + text.count(b"@") * SUBSTITUTION_SIZE
            if size > TEXT_BUFFER_SIZE:
                errors.append(
                    f"{key}: text is too long ({len(text)} bytes, with "
                    f"substitutions up to {size}; the game buffer is "
                    f"{TEXT_BUFFER_SIZE})"
                )
                continue
            snippet.text = text
            used += 1
        (imported_dir / path.name).write_bytes(dialog.to_bytes())
    for error in errors:
        print("ERROR", error)
    if errors:
        raise SystemExit(f"{len(errors)} errors")
    print(f"{used} translated strings imported into {imported_dir}")
