"""Build the translated game from the export of the translation system (SP).

The export (the project archive by token, see SP.md in the work folder or
https://translate.old-games.ru/docs/tools/): manifest.json, a table per text
translation, a folder of PNG per graphics translation. The kind of a text
translation (DDX, BOK, UI...) is told by its keys, not by its title, so renaming
a translation in SP changes nothing. The fonts and the drop caps of the books are
not in the export: they come from the repository (data/fonts, data/dropcaps).

An error in a row of a translation (a character the game font does not have,
a label wider than its button...) does not stop the build: the row stays in
English and goes to the report with a link to the phrase in SP. The report
(Markdown) also lists what the build changed on its own (wider buttons, new
book pages, moved chapter titles...) and the warnings.

Exit code: 0 built, 2 built with translation errors, 1 not built.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import traceback
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import quote

from baktt import report
from baktt.patch import patch_game
from baktt.table import read_table, write_table

SP_URL = "https://translate.old-games.ru"

# the kind of a translation by its keys (the first match)
KEY_KINDS = [
    ("LOCKS", re.compile(r"^DIAL_Z\d\d:[0-9A-F]{6}:(riddle|answer)$")),
    ("BOK", re.compile(r"^C\d\d\.BOK:\d{3}$")),
    ("EXE", re.compile(r"^EXE:")),
    ("OBJINFO", re.compile(r"^OBJINFO:\d+$")),
    ("KEYWORD", re.compile(r"^KEYWORD:\d+$")),
    ("MNAMES", re.compile(r"^MNAMES:\d+$")),
    ("PARTY", re.compile(r"^PARTY:\d+$")),
    ("MISC", re.compile(r"^(SPELLS|SPELLDOC|INVSPELL|FMAP_TWN|CRED):\d{4}$")),
    ("UI", re.compile(r"^(REQ_\w+|LBL_\w+|IN_SAVE):\d{3}$")),
    ("DDX", re.compile(r"^\w+:[0-9A-F]{6}$")),
]

CHEATS_HELP = (
    "Сборка с меню разработчиков: на основном экране зажать **правые Shift+Alt** "
    "и нажать **`~`** (английская раскладка) — следующая глава, любые предметы "
    "с описаниями, 500 золотых, статы, здоровье, заклинания и телепорты всем."
)


def key_kind(key: str) -> str | None:
    for kind, pattern in KEY_KINDS:
        if pattern.match(key):
            return kind
    return None


@dataclass
class Translation:
    id: int
    title: str
    type: str
    status: str
    path: str
    phrases: int
    done: int  # translated or redrawn
    kind: str | None = None
    errors: int = 0


def _extract(export: Path, into: Path) -> Path:
    """The export folder: unpacked from a ZIP (Cyrillic names included)."""
    if export.is_dir():
        return export
    with zipfile.ZipFile(export) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"{export}: the archive is broken ({bad})")
        zf.extractall(into)
    return into


def _translations(manifest: dict) -> list[Translation]:
    return [
        Translation(
            id=t["id"],
            title=t["title"],
            type=t["type"],
            status=t.get("status", ""),
            path=t["path"],
            phrases=t.get("phrases", 0),
            done=t.get("translated", t.get("redrawn", 0)) or 0,
        )
        for t in manifest["translations"]
    ]


def _place_texts(
    export: Path, translations: list[Translation], data: Path, problems: list[str]
) -> None:
    """Every text translation -> data/<KIND>.csv by its keys."""
    by_kind: dict[str, Translation] = {}
    for t in translations:
        if t.type != "text":
            continue
        rows = read_table(export / t.path, problems)
        kinds = {key_kind(row.key) for row in rows}
        if len(kinds) != 1 or None in kinds:
            unknown = sorted(row.key for row in rows if key_kind(row.key) is None)
            report.warning(
                f"перевод «{t.title}» пропущен: не понять вид текста по ключам "
                f"({', '.join(sorted(k for k in kinds if k)) or 'нет'}"
                + (f"; неизвестные ключи: {', '.join(unknown[:5])}" if unknown else "")
                + ")"
            )
            continue
        (kind,) = kinds
        if kind in by_kind:
            raise ValueError(
                f"two translations of {kind}: «{by_kind[kind].title}» and «{t.title}»"
            )
        t.kind = kind
        by_kind[kind] = t
        write_table(data / f"{kind}.csv", rows)
        print(f"== «{t.title}» ({t.path}) -> {kind}, {len(rows)} rows")


def _place_graphics(export: Path, translations: list[Translation], data: Path) -> None:
    for t in translations:
        if t.type != "graphics":
            continue
        folder = export / t.path
        if folder.is_dir():
            shutil.copytree(folder, data / "images" / f"sp{t.id}")
            print(f"== «{t.title}» ({t.path}) -> images")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "?"


def humanize(message: str) -> str:
    """The error message of an import in Russian (the common ones)."""
    m = re.match(r"Cannot encode character: '(.+?)', code point (\d+)", message)
    if m:
        code = int(m[2])
        name = unicodedata.name(chr(code), "?")
        return f"символ U+{code:04X} {name} — его нет в шрифте игры"
    if message == "english text does not match the game file" or message.startswith(
        "english text does not match"
    ):
        return "английский текст в СП не совпадает с игрой (оригинал правили?)"
    m = re.match(r"(.+) is (\d+) px wide, the button fits (\d+) px", message)
    if m:
        return f"{m[1]} — {m[2]} px, в кнопку влезает {m[3]} px (с расширением)"
    m = re.match(r"(.+) is (\d+) px wide, max (\d+) px", message)
    if m:
        return f"{m[1]} — {m[2]} px, место — {m[3]} px"
    if message.startswith("no text in the translation"):
        return "в переводе только имя говорящего или разметка — нет текста реплики"
    if message.startswith("must start with"):
        return "абзац книги должен начинаться с \\i или \\I, как в оригинале"
    if message in ("no such paragraph", "no such snippet"):
        return "такого места нет в игре (ключ из другой версии?)"
    return message


def _split_error(error: str) -> tuple[str, str]:
    key, sep, message = error.partition(": ")
    if not sep or " " in key:
        return "", error
    return key, message


def _render(
    *,
    manifest: dict,
    translations: list[Translation],
    collected: report.Report,
    problems: list[str],
    original: Path,
    revision: str,
    cheats: bool,
    failure: str | None,
    sp_url: str,
) -> str:
    project = manifest.get("project", {})
    by_kind = {t.kind: t for t in translations if t.kind}
    by_path = {t.path: t for t in translations}
    errors = []
    for error in collected.errors:
        key, message = _split_error(error)
        t = by_kind.get(key_kind(key)) if key else None
        if t:
            t.errors += 1
            link = f"[{key}]({sp_url}/translations/{t.id}?key={quote(key, safe='')})"
        else:
            link = key or "—"
        errors.append((t.title if t else "", link, humanize(message)))
    for problem in problems:
        path, _, rest = problem.partition(", ")
        t = by_path.get(path)
        if t:
            t.errors += 1
        rest = re.sub(r"^row (\d+): ", r"строка \1: ", rest)
        rest = rest.replace(
            "no key (column C)", "нет ключа в колонке C (фразу добавили в СП вручную?)"
        )
        rest = re.sub(r"duplicate key (\S+)", r"ключ \1 повторяется", rest)
        errors.append((t.title if t else path, "—", rest))

    now = datetime.now(UTC).strftime("%d.%m.%Y %H:%M UTC")
    if failure:
        verdict = "**не собрано** — ошибка сборки (ниже)"
    elif errors:
        verdict = (
            f"собрано, **ошибок перевода: {len(errors)}** "
            "(эти строки в сборке на английском)"
        )
    else:
        verdict = "собрано, ошибок перевода нет"
    out = [
        f"# Сборка перевода {project.get('title', '')} — {now}",
        "",
        f"Итог: {verdict}",
        "",
        f"- СП: проект {project.get('id', '?')}, "
        f"ревизия {manifest.get('revision', '?')}",
        f"- утилиты: {revision}",
        f"- оригинал: {original.name}"
        + (f" (SHA-256 {_sha256(original)[:16]}…)" if original.is_file() else ""),
        "",
    ]
    if cheats:
        out += [CHEATS_HELP, ""]
    if failure:
        out += ["## Сборка не удалась", "", "```", failure.strip(), "```", ""]
    if errors:
        out += [
            "## Ошибки перевода — исправить в СП",
            "",
            "| Перевод | Фраза | Ошибка |",
            "|---|---|---|",
        ]
        out += [f"| {t} | {link} | {_cell(msg)} |" for t, link, msg in errors]
        out.append("")
    out += [
        "## Перевод",
        "",
        "| Перевод | Вид | Статус | Фраз | Переведено | Ошибок |",
        "|---|---|---|---|---|---|",
    ]
    for t in translations:
        kind = t.kind or ("графика" if t.type == "graphics" else "пропущен")
        done = f"{t.done} перерисовано" if t.type == "graphics" else str(t.done)
        out.append(
            f"| {t.title} | {kind} | {t.status} | {t.phrases} | {done} | {t.errors} |"
        )
    out.append("")
    if collected.changes:
        out += ["## Что сборка поменяла сама — посмотреть в игре", ""]
        for section, lines in collected.changes.items():
            out.append(f"### {section} ({len(lines)})")
            out.append("")
            out += [f"- {_cell(line)}" for line in lines]
            out.append("")
    if collected.warnings:
        out += ["## Предупреждения", ""]
        out += [f"- {_cell(line)}" for line in collected.warnings]
        out.append("")
    return "\n".join(out)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def build_from_sp(
    export: Path,
    original: Path,
    output: Path,
    *,
    report_path: Path | None = None,
    fonts: Path = Path("data/fonts"),
    dropcaps: Path = Path("data/dropcaps"),
    cheats: bool = False,
    revision: str | None = None,
    sp_url: str = SP_URL,
) -> None:
    """Build the game from an SP project export.

    Parameters
    ----------
    export
        The project archive (ZIP) or its unpacked folder.
    original
        The original game ZIP (a krondor/ folder inside).
    output
        The translated game ZIP to write.
    report_path
        The Markdown report (default: OUTPUT with .md).
    fonts
        The Russian fonts (*.FNT), default data/fonts of the repository.
    dropcaps
        The Russian drop caps of the books (<letter>.png, boxes.csv), default
        data/dropcaps of the repository (may be absent).
    cheats
        Enable the developers' menu (for testers).
    revision
        The version of the tools for the report (default: git commit).
    sp_url
        The address of SP for the links in the report.
    """
    report_path = report_path or output.with_suffix(".md")
    tmp = Path(mkdtemp(prefix="bak_sp_build_"))
    manifest: dict = {}
    translations: list[Translation] = []
    problems: list[str] = []
    failure = None
    with report.collecting() as collected:
        try:
            folder = _extract(export, tmp / "export")
            manifest = json.loads((folder / "manifest.json").read_text("utf-8"))
            translations = _translations(manifest)
            data = tmp / "data"
            data.mkdir()
            if not fonts.is_dir():
                raise ValueError(f"no fonts folder {fonts}")
            shutil.copytree(fonts, data / "fonts")
            if dropcaps.is_dir():
                shutil.copytree(dropcaps, data / "dropcaps")
            _place_texts(folder, translations, data, problems)
            _place_graphics(folder, translations, data)
            for problem in problems:
                print("ERROR", problem)
            patch_game(original, output, data, cheats=cheats)
        except (Exception, SystemExit) as e:  # any failure goes to the report
            failure = "".join(traceback.format_exception_only(e))
            traceback.print_exc()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    text = _render(
        manifest=manifest,
        translations=translations,
        collected=collected,
        problems=problems,
        original=original,
        revision=revision or _git_revision(),
        cheats=cheats,
        failure=failure,
        sp_url=sp_url,
    )
    report_path.write_text(text + "\n", encoding="utf-8")
    print(f"\nReport: {report_path}")
    if failure:
        output.unlink(missing_ok=True)
        raise SystemExit(1)
    if collected.errors or problems:
        raise SystemExit(2)
