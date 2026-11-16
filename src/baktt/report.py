"""What a build found and did, for the build report (build-from-sp).

The imports of the texts collect their errors per row ("KEY: message") and skip
those rows. Outside a report (patch-game, the import commands) an error stops
the build, as always; inside `collecting()` the errors are recorded, the rows
stay in English and the build goes on. The steps that change the game on their
own (a wider button, a moved chapter title, a new book page...) and the
warnings are recorded too, and printed in both cases.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    # section -> lines
    changes: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


_current: Report | None = None


@contextmanager
def collecting() -> Iterator[Report]:
    """Record the errors instead of stopping the build."""
    global _current
    previous, _current = _current, Report()
    try:
        yield _current
    finally:
        _current = previous


def translation_errors(errors: list[str]) -> None:
    """The errors of the rows of a translation table (the rows are skipped)."""
    for error in errors:
        print("ERROR", error)
    if not errors:
        return
    if _current is None:
        raise SystemExit(f"{len(errors)} errors")
    _current.errors.extend(errors)


def change(section: str, line: str) -> None:
    """Something the build changed on its own, to be checked in the game."""
    print(f"  {line}")
    if _current is not None:
        _current.changes.setdefault(section, []).append(line)


def warning(line: str) -> None:
    print(f"  WARNING {line}")
    if _current is not None:
        _current.warnings.append(line)
