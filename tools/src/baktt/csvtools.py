import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Section:
    name: str
    strings: list[tuple[str, str]] = field(default_factory=list)


def save_sections(csv_path: Path, sections: list[Section], append=False) -> None:
    with open(csv_path, "a" if append else "w") as f:
        writer = csv.writer(f)
        for section in sorted(sections, key=lambda s: s.name):
            writer.writerow((f"==={section.name}",))
            writer.writerows(section.strings)


def load_sections(csv_path: Path) -> list[Section]:
    sections: list[Section] = []

    with open(csv_path) as f:
        reader = csv.reader(f)
        section: Optional[Section] = None
        for row in reader:
            if row[0].startswith("==="):
                section_name = row[0][3:]
                if section:
                    sections.append(section)
                section = Section(name=section_name)
            else:
                assert section is not None
                assert len(row) == 2
                section.strings.append(tuple(row))

    if section:
        sections.append(section)

    return sections
