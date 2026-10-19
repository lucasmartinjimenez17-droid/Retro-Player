"""Native Qt captures for saved albums and playlist creation, entirely offline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import ALBUMS_BY_ID
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

    def tab(name):
        next(button for button in window.tabs.buttons() if button.text() == name).click()
        settle()

    def capture(name):
        settle()
        window.grab().save(str(output / name))

    album = ALBUMS_BY_ID["moonlit-water"]
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        suffix = f"{width}x{height}.png"
        window.resize(width, height)
        window.state.set_album_saved(album.id, False)
        tab("Search")
        window.search.setText(album.name)
        row = next(row for row in window.search_result_rows if row.entity.id == album.id)
        row.click()
        capture("library-save-album-" + suffix)
        window.albums.save_button.click()
        capture("library-saved-album-" + suffix)
        tab("Playlists")
        browser = window.playlists
        browser.new_button.click()
        browser.name_input.setText("Evening by the sea")
        capture("library-new-playlist-form-" + suffix)
        browser.create_button.click()
        settle()
        browser.library_scroll.ensureWidgetVisible(browser.library_rows[-1])
        capture("library-new-playlist-" + suffix)
        playlist = browser.library_rows[-1].playlist
        browser.library_rows[-1].click()
        if width == 1120:
            capture("library-empty-playlist.png")
        for track in album.tracks:
            window.state.add_to_playlist(playlist.id, track.id)
        capture("library-playlist-songs-" + suffix)
    for album_id in list(window.state.saved_album_ids):
        window.state.set_album_saved(album_id, False)
    tab("Albums")
    capture("library-empty-albums.png")
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
