"""Review prompt 5 with native Qt fonts: python tests/render_visual_fixes.py."""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
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

    for track in (TRACKS[0], TRACKS[1], TRACKS[4], ALBUMS[0].tracks[5]):
        window.state.set_liked(track.id, True)
    for track in (ALBUMS[0].tracks[5], TRACKS[4], TRACKS[4]):
        window.state.add_to_queue(track.id)
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        window.resize(width, height)
        tab("Search")
        window.grab().save(str(output / f"ux-search-{width}x{height}.png"))
        # Deliberately leave a restrictive Search query when entering Queue.
        window.search.setText("no-match")
        tab("Queue")
        window.grab().save(str(output / f"ux-queue-{width}x{height}.png"))
        window.search.clear()
    window.resize(1120, 760)
    tab("Liked")
    window.liked.rows[1].track = replace(TRACKS[1], title="A Sunday Kind of Love — The Extended Evening Session")
    window.grab().save(str(output / "ux-liked-long-title.png"))
    tab("Albums")
    window.albums.open_album(ALBUMS[0].id)
    app.processEvents()
    window.grab().save(str(output / "ux-album-detail.png"))
    tab("Search")
    for row, name in ((window.rows[0], "unlike"), (window.rows[2], "like")):
        row.open_menu()
        app.processEvents()
        row.menu.grab().save(str(output / f"ux-{name}-menu.png"))
        row.menu.close()
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
