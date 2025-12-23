# /bin/env python3
import logging
import tkinter as tk
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import askyesno
from tkinter.ttk import LabelFrame

import bitstring
from cyclopts import App

from baktt.encoding import INVERSE_TRANSLITERATION_TABLE
from baktt.fonts import Font, Glyph

HI_RES = False


def scale(size: int) -> int:
    return size if HI_RES else size // 2


@dataclass
class DrawnGlyph:
    pixel_height: int
    pixel_width: int
    canvas: tk.Canvas
    outline: str

    def __init__(
        self,
        parent: tk.Widget,
        height: int,
        pixel_height: int,
        pixel_width: int,
        outline: str = "",
    ) -> None:
        self.pixel_height = pixel_height
        self.pixel_width = pixel_width
        self.outline = outline
        self.canvas = tk.Canvas(
            parent,
            width=16 * pixel_width,
            height=height * pixel_height,
        )

    def draw(self, glyph: Glyph) -> None:
        # clear existing pixels
        for object_id in self.canvas.find_all():
            self.canvas.delete(object_id)

        # draw pixels
        for row_idx, pixels in enumerate(glyph.to_pixels()):
            for col_idx, filled in enumerate(pixels):
                self.canvas.create_rectangle(
                    col_idx * self.pixel_width,
                    row_idx * self.pixel_height,
                    (col_idx + 1) * self.pixel_width,
                    (row_idx + 1) * self.pixel_width,
                    fill="black" if filled else "white",
                    outline=self.outline,
                )


logger = getLogger()


class Application(tk.Frame):
    CHARACTERS_PER_ROW = 12
    BASE_TITLE = "Betrayal at Krondor Font Editor"

    def __init__(self, root: tk.Tk, font_path: Path | None = None) -> None:
        self.label_frame_padding = scale(10)
        self.frame_padding = scale(5)

        super().__init__(root, padx=self.frame_padding, pady=self.frame_padding)
        self.root = root
        self.root.title(self.BASE_TITLE)

        self.grid()
        self.create_widgets()
        self.font: Font | None = None
        self.characters: list[Character] = []
        self._edited_character: Character | None = None
        self.undo_stack: list[Glyph] = []
        self._font_path: Path | None = None
        if font_path:
            self.open_font(font_path)
        else:
            self.open_font_dialog()

        self.copied_glyph: Glyph | None = None

    def create_widgets(self) -> None:
        top = self.winfo_toplevel()
        self.menu_bar = tk.Menu(top)
        top["menu"] = self.menu_bar

        # List of characters
        self.available_characters_frame = LabelFrame(
            self, text="Characters", padding=self.label_frame_padding
        )
        self.available_characters_frame.pack(
            side=tk.LEFT, padx=self.frame_padding, pady=self.frame_padding
        )

        right_panel = tk.Frame(self, width=scale(500))
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        # Editor area
        self.editor_frame = LabelFrame(
            right_panel, text="Editor", padding=self.label_frame_padding
        )
        self.editor_frame.pack(
            side=tk.TOP, padx=self.frame_padding, pady=self.frame_padding, fill=tk.BOTH
        )

        # Editor controls
        self.editor_controls_frame = tk.Frame(right_panel)
        self.editor_controls_frame.pack(
            side=tk.TOP, padx=self.frame_padding, pady=self.frame_padding, fill=tk.X
        )

        # Character width control
        self.character_width_control_value = tk.StringVar()
        self.character_width_control = tk.Spinbox(
            self.editor_controls_frame,
            values=[str(i) for i in range(1, 17)],
            width=2,
            state="disabled",
            textvariable=self.character_width_control_value,
            command=self.set_character_width,
        )
        self.character_width_control.pack(side=tk.RIGHT)
        tk.Label(self.editor_controls_frame, text="Character width: ").pack(
            side=tk.RIGHT
        )

        # Clear character button
        self.clear_character_button = tk.Button(
            self.editor_controls_frame,
            text="Clear",
            command=self.clear_editor,
            state="disabled",
        )
        self.clear_character_button.pack(side=tk.LEFT)

        # Menu Bar
        self.menu_bar.add_command(
            label="Open", command=self.open_font_dialog, accelerator="^o"
        )
        self.menu_bar.add_command(label="Save", command=self.save, accelerator="^s")
        self.menu_bar.add_command(label="Save As", command=self.save_as_dialog)
        self.menu_bar.add_command(label="Undo", command=self.undo, accelerator="^z")
        self.menu_bar.add_command(label="Quit", command=self.quit, accelerator="^z")

        # Shortcuts
        self.root.bind("<Control-o>", lambda _: self.open_font_dialog())
        self.root.bind("<Control-s>", lambda _: self.save())
        self.root.bind("<Control-z>", lambda _: self.undo())
        self.root.bind("<Control-q>", lambda _: self.quit())
        self.root.bind("<Control-c>", lambda _: self.copy_glyph())
        self.root.bind("<Control-v>", lambda _: self.paste_glyph())

    @property
    def font_path(self) -> Path | None:
        return self._font_path

    @font_path.setter
    def font_path(self, path: Path | None) -> None:
        self._font_path = path
        if path:
            self.root.title(f"{self.BASE_TITLE} - {path.name}")
        else:
            self.root.title(self.BASE_TITLE)

    def quit(self) -> None:
        if askyesno(message="Are you sure you want to quit?"):
            self.master.destroy()

    def open_font(self, path: Path) -> None:
        self.font = Font.from_file(path)
        self.font_path = path
        self.edited_character = None
        self.characters = []

        for char_idx, glyph in enumerate(self.font.glyphs, self.font.first):
            char = INVERSE_TRANSLITERATION_TABLE.get(char_idx, chr(char_idx))
            character = Character(self, char_idx, char, glyph)
            self.characters.append(character)

        self.draw_available_characters()
        self.root.minsize(width=self.winfo_reqwidth(), height=self.winfo_reqheight())

    def open_font_dialog(self) -> None:
        filename = askopenfilename(
            title="Open .FNT file", filetypes=(("FNT", "*.FNT"),)
        )
        if not filename:
            return
        self.open_font(Path(filename))

    def draw_available_characters(self) -> None:
        for child in self.available_characters_frame.winfo_children():
            child.destroy()

        if not self.font:
            return

        for i, character in enumerate(self.characters):
            drawn_glyph = DrawnGlyph(
                self.available_characters_frame, self.font.height, scale(4), scale(4)
            )
            character_btn = tk.Button(
                self.available_characters_frame,
                text=character.char,
                width=3,
                command=character.open_in_editor,
            )
            character_btn.grid(
                row=(i // self.CHARACTERS_PER_ROW) * 2,
                column=i % self.CHARACTERS_PER_ROW,
                sticky=tk.NW,
            )

            drawn_glyph.draw(character.glyph)
            drawn_glyph.canvas.grid(
                row=(i // self.CHARACTERS_PER_ROW) * 2 + 1,
                column=i % self.CHARACTERS_PER_ROW,
            )
            character.drawn_glyph = drawn_glyph

    def open_character_in_editor(self, character: Character | None) -> None:
        assert self.font is not None

        if self.edited_character:
            self.edited_character.edited_drawn_glyph = None

        for child in self.editor_frame.winfo_children():
            child.destroy()

        if character is None:
            self.character_width_control.configure(state=tk.DISABLED)
            self.clear_character_button.configure(state=tk.DISABLED)
            return

        self.clear_character_button.configure(state=tk.NORMAL)

        glyph = character.glyph

        self.character_width_control.configure(state="readonly")
        self.character_width_control_value.set(str(glyph.width))

        drawn_glyph = DrawnGlyph(
            self.editor_frame, self.font.height, scale(30), scale(30), outline="gray"
        )
        character.edited_drawn_glyph = drawn_glyph
        drawn_glyph.draw(glyph)
        drawn_glyph.canvas.grid()

        drawn_glyph.canvas.bind("<Button 1>", self.editor_left_click)
        drawn_glyph.canvas.bind("<Button 3>", self.editor_right_click)

    def editor_left_click(self, event: tk.Event) -> None:
        self.edit_pixel(event.x, event.y, False)

    def editor_right_click(self, event: tk.Event) -> None:
        self.edit_pixel(event.x, event.y, True)

    def edit_pixel(self, x: int, y: int, erase: bool) -> None:
        assert self.edited_character
        row_idx = y // scale(30)
        col_idx = x // scale(30)
        if col_idx >= self.edited_character.glyph.width:
            return

        pixels = self.edited_character.glyph.to_pixels()
        if erase:
            pixels[row_idx].overwrite("0b0", col_idx)
        else:
            pixels[row_idx].overwrite("0b1", col_idx)

        self.undo_stack.append(self.edited_character.glyph)
        self.edited_character.glyph = Glyph.from_pixels(pixels)
        self.edited_character.redraw()

    @property
    def edited_character(self) -> Character | None:
        return self._edited_character

    @edited_character.setter
    def edited_character(self, c: Character | None) -> None:
        assert self.font
        self._edited_character = c
        self.undo_stack = []
        self.open_character_in_editor(c)

    def set_character_width(self) -> None:
        assert self.edited_character is not None
        new_width = int(self.character_width_control_value.get())
        assert 1 <= new_width <= 16
        glyph = self.edited_character.glyph
        if new_width == glyph.width:
            return

        self.undo_stack.append(glyph)

        pixels = glyph.to_pixels()
        if new_width > glyph.width:
            suffix = bitstring.BitArray(uint=0, length=new_width - glyph.width)
            for row in pixels:
                row.append(suffix)
        elif new_width < glyph.width:
            pixels = [row[:new_width] for row in pixels]
        else:
            raise AssertionError()

        glyph = Glyph.from_pixels(pixels)
        self.edited_character.glyph = glyph
        self.edited_character.redraw()

    def undo(self) -> None:
        if not self.undo_stack:
            return
        assert self.edited_character
        self.edited_character.glyph = self.undo_stack.pop()
        self.edited_character.redraw()

    def save(self) -> None:
        if not self.font:
            return
        assert self.font_path
        self.font.glyphs = [c.glyph for c in self.characters]
        self.font.to_file(self.font_path)

    def save_as_dialog(self) -> None:
        filename = asksaveasfilename(title="Save as", defaultextension="FNT")
        if not filename:
            return
        self.font_path = Path(filename)
        self.save()

    def clear_editor(self) -> None:
        assert self.edited_character is not None
        assert self.font is not None
        self.undo_stack.append(self.edited_character.glyph)
        self.edited_character.glyph = Glyph(
            width=self.edited_character.glyph.width, rows=[0] * self.font.height
        )
        self.edited_character.redraw()

    def copy_glyph(self) -> None:
        if self.edited_character is None:
            return
        self.copied_glyph = self.edited_character.glyph.copy()

    def paste_glyph(self) -> None:
        if self.edited_character is None:
            return
        if self.copied_glyph is None:
            return
        self.undo_stack.append(self.edited_character.glyph)
        self.character_width_control_value.set(str(self.copied_glyph.width))
        self.edited_character.glyph = self.copied_glyph.copy()
        self.edited_character.redraw()


@dataclass
class Character:
    app: Application = field(repr=False)
    idx: int
    char: str
    glyph: Glyph
    drawn_glyph: DrawnGlyph | None = field(repr=False, default=None)
    edited_drawn_glyph: DrawnGlyph | None = field(repr=False, default=None)

    def open_in_editor(self) -> None:
        self.app.edited_character = self

    def redraw(self) -> None:
        if self.drawn_glyph:
            self.drawn_glyph.draw(self.glyph)
        if self.edited_drawn_glyph:
            self.edited_drawn_glyph.draw(self.glyph)


def start_gui(font_path: Path | None = None) -> None:
    root = tk.Tk()
    root.resizable(width=False, height=False)
    root.option_add("*tearOff", tk.FALSE)
    if root.winfo_screenwidth() > 1920:
        global HI_RES
        HI_RES = True
    app = Application(root, font_path=font_path)
    app.mainloop()


app = App(name="font-editor", help="Font editor")


def main() -> None:
    app()


@app.default
def start(font_path: Path | None = None, *, debug: bool = False) -> None:
    """Start the font editor."""
    logging.basicConfig()
    logger.setLevel(logging.DEBUG if debug else logging.ERROR)

    start_gui(font_path=font_path)


if __name__ == "__main__":
    main()
