from cyclopts import App

from baktt import (
    book,
    dialog,
    exe_patch,
    exe_text,
    fonts,
    images,
    keyword,
    misc,
    mnames,
    objinfo,
    party,
    resources,
    sp_graphics,
    ui,
)
from baktt.build_from_sp import build_from_sp
from baktt.export_all import export_all
from baktt.patch import patch_game

try:
    from baktt.gui import font_editor
except ImportError:
    font_editor = None

app = App(name="baktt", help="Bak translation tools")

app.command(resources.app)
app.command(fonts.app)
app.command(book.app)
app.command(dialog.app)
app.command(objinfo.app)
app.command(keyword.app)
app.command(mnames.app)
app.command(party.app)
app.command(ui.app)
app.command(misc.app)
app.command(images.app)
app.command(sp_graphics.app)
app.command(exe_patch.app)
app.command(exe_text.app)
app.command(patch_game)
app.command(export_all, name="export-all")
app.command(build_from_sp, name="build-from-sp")

if font_editor is not None:
    gui_app = App(name="gui", help="GUI utilities")
    gui_app.command(font_editor.app)
    app.command(gui_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
