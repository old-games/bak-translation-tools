from cyclopts import App

from baktt import book, fonts, images, resources
from baktt.patch import patch_game

try:
    from baktt.gui import font_editor
except ImportError:
    font_editor = None

app = App(name="baktt", help="Bak translation tools")

app.command(resources.app)
app.command(fonts.app)
app.command(book.app)
app.command(images.app)
app.command(patch_game)

if font_editor is not None:
    gui_app = App(name="gui", help="GUI utilities")
    gui_app.command(font_editor.app)
    app.command(gui_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
