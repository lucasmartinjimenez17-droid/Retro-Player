"""Generate local review captures: python tests/render_song_management.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import ALBUMS, TRACKS
from ui.widgets import cover_art, deck_texture


def render():
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    output = Path(__file__).resolve().parents[1] / "docs"

    def tab(name):
        next(button for button in window.tabs.buttons() if button.text() == name).click()
        app.processEvents()
        app.processEvents()

    tab("Liked")
    window.grab().save(str(output / "liked-empty.png"))
    for track in (*TRACKS, *ALBUMS[0].tracks[2:6]):
        window.state.set_liked(track.id, True)
    window._show_track(ALBUMS[0].tracks[2])
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        window.resize(width, height)
        tab("Liked")
        window.grab().save(str(output / f"liked-{width}x{height}.png"))
    window.resize(1400, 900)
    tab("Liked")
    row = window.liked.rows[0]
    row.open_menu()
    app.processEvents()
    row.menu.grab().save(str(output / "song-options-menu.png"))
    # Qt menus are separate native windows: composite their actual widget captures.
    capture = window.grab()
    painter = QPainter(capture)
    painter.drawPixmap(window.mapFromGlobal(row.menu.pos()), row.menu.grab())
    painter.end()
    capture.save(str(output / "song-options.png"))
    submenu = row.playlist_menu
    action = row.menu.actions()[1]
    rect = row.menu.actionGeometry(action)
    submenu.popup(row.menu.mapToGlobal(QPoint(rect.right(), rect.top())))
    app.processEvents()
    submenu.grab().save(str(output / "playlist-selector.png"))
    submenu.close()
    row.menu.close()
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
