"""Local artist portraits and a reusable, fully scrolling artist profile."""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.albums import AlbumCard
from ui.mock_data import ALBUMS, ARTISTS_BY_ID, TRACKS_BY_ID
from ui.widgets import TrackRow, scroll_area


def artist_art(colors, size=128):
    """Small abstract portrait drawn locally, distinct from a square record sleeve."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 128, size / 128)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(colors[0]))
    painter.drawEllipse(QRectF(0, 0, 128, 128))
    painter.setBrush(QColor(colors[2]))
    painter.drawEllipse(QRectF(22, 69, 84, 52))
    painter.setBrush(QColor(colors[1]))
    painter.drawEllipse(QRectF(44, 25, 40, 47))
    painter.end()
    return pixmap


class ArtistProfile(QWidget):
    track_requested = Signal(object)
    album_requested = Signal(str)
    back_requested = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.artist_id = None
        self.current_track = None
        self.is_playing = True
        self.track_rows = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.back_button = QPushButton("‹   Search results")
        self.back_button.setObjectName("libraryBack")
        self.back_button.setAccessibleName("Back to Search results")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.back_requested)
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        content = QWidget()
        sections = QVBoxLayout(content)
        sections.setContentsMargins(0, 0, 4, 0)
        sections.setSpacing(18)
        header = QHBoxLayout()
        header.setSpacing(14)
        self.portrait = QLabel()
        self.portrait.setFixedSize(82, 82)
        header.addWidget(self.portrait)
        info = QVBoxLayout()
        info.setSpacing(5)
        label = QLabel("Artist")
        label.setObjectName("count")
        info.addWidget(label)
        self.name = QLabel()
        self.name.setObjectName("playlistTitle")
        self.name.setWordWrap(True)
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.addWidget(self.name)
        header.addLayout(info, 1)
        sections.addLayout(header)
        self.song_count = self._heading(sections, "Songs")
        self.songs = QVBoxLayout()
        self.songs.setSpacing(5)
        sections.addLayout(self.songs)
        self.empty_songs = QLabel("No songs available in this catalogue yet.")
        self.empty_songs.setObjectName("artist")
        self.empty_songs.setWordWrap(True)
        sections.addWidget(self.empty_songs)
        self.album_count = self._heading(sections, "Albums")
        self.album_grid = QGridLayout()
        self.album_grid.setHorizontalSpacing(12)
        self.album_grid.setVerticalSpacing(12)
        self.album_grid.setColumnStretch(0, 1)
        self.album_grid.setColumnStretch(1, 1)
        # Keep both columns at the same width even for an artist with one release.
        self.album_grid.setColumnMinimumWidth(0, 120)
        self.album_grid.setColumnMinimumWidth(1, 120)
        self.album_cards = []
        for album in ALBUMS:
            card = AlbumCard(album, content)
            card.clicked.connect(lambda checked=False, album_id=album.id: self.album_requested.emit(album_id))
            card.hide()
            self.album_cards.append(card)
        sections.addLayout(self.album_grid)
        self.empty_albums = QLabel("No albums available in this catalogue yet.")
        self.empty_albums.setObjectName("artist")
        self.empty_albums.setWordWrap(True)
        sections.addWidget(self.empty_albums)
        sections.addStretch()
        self.scroll = scroll_area(content)
        layout.addWidget(self.scroll, 1)

    @staticmethod
    def _heading(layout, title):
        line = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        line.addWidget(label, 1)
        count = QLabel()
        count.setObjectName("count")
        line.addWidget(count)
        layout.addLayout(line)
        return count

    def open_artist(self, artist_id):
        artist = ARTISTS_BY_ID[artist_id]
        self.artist_id = artist_id
        self.name.setText(artist.name)
        self.portrait.setPixmap(artist_art(artist.colors, 82))
        tracks = [TRACKS_BY_ID[track_id] for track_id in artist.track_ids]
        while len(self.track_rows) < len(tracks):
            row = TrackRow(tracks[len(self.track_rows)], None, state=self.state)
            row.clicked.connect(lambda checked=False, item=row: self.track_requested.emit(item.track))
            self.songs.addWidget(row)
            self.track_rows.append(row)
        for position, row in enumerate(self.track_rows):
            row.setVisible(position < len(tracks))
            if position < len(tracks):
                row.track = tracks[position]
                row.setAccessibleName(f"{row.track.title}, {row.track.artist}")
                row.setToolTip(f"{row.track.title} · {row.track.album}")
        self.song_count.setText(str(len(tracks)))
        self.empty_songs.setVisible(not tracks)
        for card in self.album_cards:
            self.album_grid.removeWidget(card)
            card.hide()
            card.setChecked(False)
        cards_by_id = {card.album.id: card for card in self.album_cards}
        for position, album_id in enumerate(artist.album_ids):
            card = cards_by_id[album_id]
            self.album_grid.addWidget(card, position // 2, position % 2)
            card.show()
        self.album_count.setText(str(len(artist.album_ids)))
        self.empty_albums.setVisible(not artist.album_ids)
        self.sync_playback(self.current_track, self.is_playing)
        self.scroll.verticalScrollBar().setValue(0)
        self.back_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def sync_playback(self, track, playing):
        self.current_track, self.is_playing = track, playing
        for row in self.track_rows:
            row.setChecked(track is not None and row.track.id == track.id)
            row.playing = playing
            row.update()
