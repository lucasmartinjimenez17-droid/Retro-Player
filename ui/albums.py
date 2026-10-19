"""Two-column album library and numbered track detail, without playback logic."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ui.mock_data import ALBUMS, ALBUMS_BY_ID, Album, time_text
from ui.session import SessionState
from ui.widgets import CollectionHeader, TrackRow, cover_art, font, scroll_area


class AlbumCard(QPushButton):
    """A square sleeve above compact, elided metadata; the whole card opens detail."""
    def __init__(self, album: Album, parent=None):
        super().__init__(parent)
        self.album = album
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setMinimumWidth(120)
        year = f" · {album.year}" if album.year is not None else ""
        self.setAccessibleName(f"Open album {album.name}, {album.artist}{year}")
        self.setToolTip(f"{album.name}\n{album.artist}{year}")

    def sizeHint(self):
        return QSize(170, self.heightForWidth(170))

    def minimumSizeHint(self):
        return QSize(120, self.heightForWidth(120))

    def heightForWidth(self, width):
        return width + 82

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # QScrollArea can otherwise keep a grid row at its initial size hint.
        # Only height follows width; column widths remain controlled by the layout.
        height = self.heightForWidth(self.width())
        if self.minimumHeight() != height or self.maximumHeight() != height:
            self.setFixedHeight(height)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        bg = "#30404d" if self.isDown() else (
            "#24333e" if self.isChecked() else "#1d2b36" if self.underMouse() else "#00000000")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 9, 9)
        side = self.width() - 16
        p.drawPixmap(8, 8, side, side, cover_art(self.album.colors))
        p.setPen(QColor("#f0e8dc"))
        p.setFont(font(14))
        p.drawText(QRectF(8, side + 18, side, 22), p.fontMetrics().elidedText(
            self.album.name, Qt.TextElideMode.ElideRight, side))
        p.setFont(font(12))
        p.setPen(QColor("#a5adb4"))
        p.drawText(QRectF(8, side + 41, side, 20), p.fontMetrics().elidedText(
            self.album.artist, Qt.TextElideMode.ElideRight, side))
        p.setFont(font(11))
        p.setPen(QColor("#b99f7d"))
        p.drawText(QRectF(8, side + 63, side - 20, 18),
                   str(self.album.year) if self.album.year is not None else "Album")
        x, y = self.width() - 17, side + 71
        p.drawLine(QPointF(x - 3, y - 4), QPointF(x + 1, y))
        p.drawLine(QPointF(x + 1, y), QPointF(x - 3, y + 4))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#b99a71"), 1.5))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 8, 8)


class AlbumBrowser(QStackedWidget):
    track_requested = Signal(object)
    play_requested = Signal(object)
    back_requested = Signal()

    def __init__(self, parent=None, state=None):
        super().__init__(parent)
        self.state = state if state is not None else SessionState(self)
        self.external_back = False
        self.selected_album_id = None
        self.current_track = None
        self.is_playing = True
        self.cards = []
        self.track_rows = []
        self._build_library()
        self._build_detail()
        self.state.saved_albums_changed.connect(self._refresh_saved_albums)
        self._refresh_saved_albums()

    def _build_library(self):
        self.library_page = QWidget()
        layout = QVBoxLayout(self.library_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        title = QLabel("Your Albums")
        title.setObjectName("libraryTitle")
        heading.addWidget(title, 1)
        self.library_count = QLabel()
        self.library_count.setObjectName("count")
        heading.addWidget(self.library_count)
        layout.addLayout(heading)
        content = QWidget()
        self.library_content = content
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(0, 0, 4, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.all_cards = []
        for album in self.state.albums.values():
            card = AlbumCard(album, content)
            card.clicked.connect(lambda checked=False, album_id=album.id: self.open_album(album_id))
            card.hide()
            self.all_cards.append(card)
        self.empty_library = QLabel("Your next favorite record is waiting.\nExplore Search or an artist and choose Save album.", content)
        self.empty_library.setObjectName("artist")
        self.empty_library.setWordWrap(True)
        self.empty_library.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_library.setMinimumHeight(180)
        self.library_scroll = scroll_area(content)
        layout.addWidget(self.library_scroll, 1)
        self.addWidget(self.library_page)

    def _build_detail(self):
        self.detail_page = QWidget()
        layout = QVBoxLayout(self.detail_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.back_button = QPushButton("‹   Your Albums")
        self.back_button.setObjectName("libraryBack")
        self.back_button.setAccessibleName("Back to Your Albums")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self._go_back)
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.header = CollectionHeader("Play album")
        self.header.artist.show()
        self.header.play_button.clicked.connect(self._request_play)
        self.save_button = QPushButton("Save album")
        self.save_button.setObjectName("secondaryAction")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self._toggle_saved)
        self.header.info_layout.addWidget(self.save_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.header)
        heading = QHBoxLayout()
        title = QLabel("Tracks")
        title.setObjectName("sectionTitle")
        heading.addWidget(title, 1)
        self.total_time = QLabel()
        self.total_time.setObjectName("count")
        heading.addWidget(self.total_time)
        layout.addLayout(heading)
        content = QWidget()
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 4, 0)
        rows.setSpacing(3)
        # A small reusable pool; navigation never creates duplicate rows or callbacks.
        for position in range(max(len(album.tracks) for album in ALBUMS)):
            row = TrackRow(ALBUMS[0].tracks[0], position, state=self.state)
            row.track_number = position + 1
            row.clicked.connect(lambda checked=False, item=row: self.track_requested.emit(item.track))
            rows.addWidget(row)
            self.track_rows.append(row)
        rows.addStretch()
        self.detail_scroll = scroll_area(content)
        layout.addWidget(self.detail_scroll, 1)
        self.addWidget(self.detail_page)

    def show_library(self, reset_scroll=False, restore_focus=False):
        self.external_back = False
        self.setCurrentWidget(self.library_page)
        if reset_scroll:
            self.library_scroll.verticalScrollBar().setValue(0)
        for card in self.cards:
            card.setChecked(card.album.id == self.selected_album_id)
            if restore_focus and card.isChecked():
                card.setFocus(Qt.FocusReason.OtherFocusReason)

    def _refresh_saved_albums(self):
        for card in self.all_cards:
            self.grid.removeWidget(card)
            card.hide()
        self.grid.removeWidget(self.empty_library)
        cards_by_id = {card.album.id: card for card in self.all_cards}
        self.cards = [cards_by_id[album_id] for album_id in self.state.saved_album_ids]
        for position, card in enumerate(self.cards):
            self.grid.addWidget(card, position // 2, position % 2)
            card.show()
        if not self.cards:
            self.grid.addWidget(self.empty_library, 0, 0, 1, 2)
        self.empty_library.setVisible(not self.cards)
        self.library_count.setText(f"{len(self.cards)} albums")
        self._sync_save_button()

    def _sync_save_button(self):
        saved = self.selected_album_id in self.state.saved_album_ids
        self.save_button.setText("Remove from library" if saved else "Save album")
        if self.selected_album_id is not None:
            self.save_button.setAccessibleName(f"{self.save_button.text()}: {self.state.albums[self.selected_album_id].name}")

    def _toggle_saved(self):
        if self.selected_album_id is not None:
            self.state.set_album_saved(self.selected_album_id,
                                       self.selected_album_id not in self.state.saved_album_ids)

    def _go_back(self):
        if self.external_back:
            self.back_requested.emit()
        else:
            self.show_library(restore_focus=True)

    def open_album(self, album_id, back_label=None):
        album = ALBUMS_BY_ID[album_id]
        self.external_back = back_label is not None
        destination = back_label or "Your Albums"
        self.back_button.setText(f"‹   {destination}")
        self.back_button.setAccessibleName(f"Back to {destination}")
        self.selected_album_id = album.id
        self._sync_save_button()
        self.header.title.setText(album.name)
        self.header.title.setToolTip(album.name)
        self.header.artist.setText(album.artist)
        year = f"{album.year} · " if album.year is not None else ""
        self.header.metadata.setText(f"{year}{len(album.tracks)} songs")
        self.header.cover.setPixmap(cover_art(album.colors).scaled(
            82, 82, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.header.play_button.setEnabled(bool(album.tracks))
        self.header.play_button.setAccessibleName(f"Play album {album.name}")
        self.total_time.setText(time_text(sum(track.seconds for track in album.tracks)))
        for position, row in enumerate(self.track_rows):
            visible = position < len(album.tracks)
            row.setVisible(visible)
            if visible:
                row.track = album.tracks[position]
                row.setAccessibleName(f"Track {position + 1}. {row.track.title}, {row.track.artist}")
                row.setToolTip(f"{position + 1}. {row.track.title}\n{row.track.artist} · {time_text(row.track.seconds)}")
        self.sync_playback(self.current_track, self.is_playing)
        self.setCurrentWidget(self.detail_page)
        self.detail_scroll.verticalScrollBar().setValue(0)
        self.back_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def sync_playback(self, track, playing):
        self.current_track, self.is_playing = track, playing
        for row in self.track_rows:
            row.setChecked(row.track == track)
            row.playing = playing
            row.update()

    def _request_play(self):
        if self.selected_album_id is not None:
            album = ALBUMS_BY_ID[self.selected_album_id]
            if album.tracks:
                self.play_requested.emit(album.tracks[0])
