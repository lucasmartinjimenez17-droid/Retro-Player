"""Offline native Qt captures and successive frames of the playback indicator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtTest import QTest
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

    for size in ((1120, 760), (1400, 900), (1680, 1050)):
        window.resize(*size)
        tab("Search")
        window.search.setText(TRACKS[0].title)
        window.top_rows[0].click()
        window.state.set_liked(TRACKS[0].id, True)
        QTest.qWait(180)
        window.grab().save(str(output / f"playback-search-{size[0]}x{size[1]}.png"))

    tab("Albums")
    window.albums.open_album(ALBUMS[0].id)
    window.albums.track_rows[0].click()
    QTest.qWait(100)
    window.grab().save(str(output / "playback-album.png"))
    row = window.albums.track_rows[0]
    frames = []
    for _ in range(5):
        QTest.qWait(180)
        frames.append(row.grab())
    window.play_button.click()
    QTest.qWait(100)
    frames.append(row.grab())
    sheet = QPixmap(row.width(), row.height() * len(frames))
    sheet.fill(QColor("#17232e"))
    painter = QPainter(sheet)
    for i, frame in enumerate(frames):
        painter.drawPixmap(0, i * row.height(), frame)
    painter.end()
    sheet.save(str(output / "playback-frames.png"))
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
