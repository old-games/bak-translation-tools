"""Widgets of the REQ screens: size and place of the buttons.

A REQ file (REQ_*.DAT, COMBAT/CONTENTS/SHOOT/SPELL.DAT): 28-byte header (the
window x, y, width, height at +6; the widgets are relative to its corner; some
screens have a dummy 1x1 or 10x10 window: then the screen is the limit),
u16 count at +28, 33-byte widget records, u16 pool size, string pool. A record:
u16 type at +0 (3 = image button, 6 = text button), x, y, width, height (int16)
at +0x0B, u16 image number at +0x19 (image buttons), label offset at +0x15.

The game draws a text button with the frame of the width of its record and
takes clicks in the record rectangle (checked in the emulator 17.11: REQ_INFO
"Exit" 26 -> 34 px), so a button grows by changing the record. What is drawn
under it (the background picture) is not known here: a text button grows by
at most MAX_GROW px, and every change is reported to be checked on the screen.

Image buttons: number n -> BICONS1/BICONS2 (file 0x1D6F7): n > 50 -> n + 1,
then odd -> BICONS2.BMX (pressed), even -> BICONS1.BMX, image n / 2. The record
size is not always the image size (round buttons are 1 px larger), so a
redrawn image of another size changes the record by the same difference.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

HEADER_SIZE = 28
RECORD_SIZE = 33
TYPE_IMAGE = 3
TYPE_TEXT = 6
SCREEN = (320, 200)
WINDOW_POS = 6
MAX_GROW = 16
# REQ-format files with widgets the game loads besides the REQ_*.DAT with texts
# (KRONDOR.EXE has their names)
OTHER_FILES = ["COMBAT.DAT", "CONTENTS.DAT", "SHOOT.DAT", "SPELL.DAT"]


@dataclass
class Widget:
    pos: int  # file offset of the record
    type: int
    x: int
    y: int
    w: int
    h: int
    image: int
    label: int

    def overlaps(self, other: Widget) -> bool:
        return (
            self.x < other.x + other.w
            and other.x < self.x + self.w
            and self.y < other.y + other.h
            and other.y < self.y + self.h
        )


def widgets(data: bytes) -> list[Widget]:
    (count,) = struct.unpack_from("<H", data, HEADER_SIZE)
    result = []
    for i in range(count):
        pos = HEADER_SIZE + 2 + RECORD_SIZE * i
        (type_,) = struct.unpack_from("<H", data, pos)
        x, y, w, h = struct.unpack_from("<4h", data, pos + 0x0B)
        (label,) = struct.unpack_from("<h", data, pos + 0x15)
        (image,) = struct.unpack_from("<h", data, pos + 0x19)
        result.append(Widget(pos, type_, x, y, w, h, image, label))
    return result


def set_geometry(data: bytearray, widget: Widget) -> None:
    struct.pack_into(
        "<4h", data, widget.pos + 0x0B, widget.x, widget.y, widget.w, widget.h
    )


def image_of(number: int) -> tuple[str, int]:
    """(BICONS file, image index) of an image button number."""
    n = number + 1 if number > 50 else number
    return ("BICONS2.BMX" if n % 2 else "BICONS1.BMX"), n // 2


def bounds(data: bytes) -> tuple[int, int]:
    """The area the widgets of a REQ file must stay in (relative)."""
    x, y, w, h = struct.unpack_from("<4h", data, WINDOW_POS)
    all_widgets = widgets(data)
    right = max((wd.x + wd.w for wd in all_widgets), default=0)
    bottom = max((wd.y + wd.h for wd in all_widgets), default=0)
    if w >= right and h >= bottom:
        return w, h
    return SCREEN[0] - x, SCREEN[1] - y


def _placed(
    widget: Widget, others: list[Widget], original: Widget, area: tuple[int, int]
) -> bool:
    """In the area and not over a widget the original was not over."""
    if widget.x < 0 or widget.y < 0:
        return False
    if widget.x + widget.w > area[0] or widget.y + widget.h > area[1]:
        return False
    return all(
        not widget.overlaps(other) or original.overlaps(other) for other in others
    )


def widen(widget: Widget, width: int, data: bytes) -> Widget | None:
    """The text button `width` wide around the same center, or None if it
    does not fit: grows by more than MAX_GROW, goes out of the window or over
    a widget it was not over before (`data` is the REQ file)."""
    grow = width - widget.w
    if grow > MAX_GROW:
        return None
    new = Widget(**{**widget.__dict__, "x": widget.x - grow // 2, "w": width})
    others = [w for w in widgets(data) if w.pos != widget.pos]
    return new if _placed(new, others, widget, bounds(data)) else None


def max_width(widget: Widget, data: bytes) -> int:
    """The widest the text button can grow to around its center."""
    width = widget.w
    while widen(widget, width + 1, data):
        width += 1
    return width


def resize_image_buttons(
    resources_dir: Path, files: list[str], sizes: dict[tuple[str, int], tuple[int, int]]
) -> list[str]:
    """Change the image buttons whose image changes size: `sizes` is
    (BICONS file, index) -> (width change, height change). The button keeps
    its left top corner (an artist draws the wider button into the free space
    on its right). Returns a report; off the screen or over another widget is
    an error."""
    report = []
    errors = []
    for name in files:
        path = resources_dir / name
        data = bytearray(path.read_bytes())
        all_widgets = widgets(data)
        changed = False
        for widget in all_widgets:
            if widget.type != TYPE_IMAGE or widget.image < 0:
                continue
            delta = sizes.get(image_of(widget.image))
            if not delta or delta == (0, 0):
                continue
            new = Widget(
                **{
                    **widget.__dict__,
                    "w": widget.w + delta[0],
                    "h": widget.h + delta[1],
                }
            )
            others = [w for w in all_widgets if w.pos != widget.pos]
            file, index = image_of(widget.image)
            where = f"{name}: button {file}_{index} at {widget.x},{widget.y}"
            if not _placed(new, others, widget, bounds(data)):
                errors.append(
                    f"{where}: {new.w}x{new.h} px is off the screen or over "
                    "another widget"
                )
                continue
            set_geometry(data, new)
            changed = True
            report.append(f"{where}: {widget.w}x{widget.h} -> {new.w}x{new.h} px")
        if changed:
            path.write_bytes(bytes(data))
    if errors:
        raise ValueError("\n".join(errors))
    return report
