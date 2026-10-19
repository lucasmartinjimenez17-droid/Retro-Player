"""Render Search exploration with native Qt fonts, without network or audio."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import ALBUMS, ARTISTS, TRACKS
from ui.widgets import cover_art, deck_texture


def render():
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    output = Path(__file__).resolve().parents[1] / "docs"

    def settle():
        app.processEvents()
        app.processEvents()

    def result(kind, entity_id):
        row = next(r for r in window.search_result_rows if r.kind == kind and r.entity.id == entity_id)
        window.catalog_scroll.ensureWidgetVisible(row)
        settle()
        row.click()
        settle()

    for track in (TRACKS[0], TRACKS[4], ALBUMS[3].tracks[1]):
        window.state.set_liked(track.id, True)
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        window.resize(width, height)
        window.search.setText("The Velvet Hours")
        settle()
        window.grab().save(str(output / f"search-results-{width}x{height}.png"))
        result("album", ALBUMS[0].id)
        window.grab().save(str(output / f"search-album-{width}x{height}.png"))
        window.albums.back_button.click()
        settle()
        window.search.setText("Nina")
        result("artist", ARTISTS[3].id)
        window.grab().save(str(output / f"artist-profile-{width}x{height}.png"))
        card = window.artist_profile.album_cards[3]
        window.artist_profile.scroll.ensureWidgetVisible(card)
        settle()
        if width == 1120:
            window.grab().save(str(output / "artist-profile-albums-small.png"))
        card.click()
        settle()
        window.grab().save(str(output / f"artist-album-{width}x{height}.png"))
        window.albums.back_button.click()
        settle()
        window.artist_profile.back_button.click()
        settle()
    window.search.setText(ARTISTS[-1].name)
    result("artist", ARTISTS[-1].id)
    window.grab().save(str(output / "artist-profile-empty.png"))
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
