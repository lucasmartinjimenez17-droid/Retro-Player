"""Library/detail navigation contained entirely inside the sidebar."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ui.mock_data import PLAYLISTS, TRACKS, TRACKS_BY_ID, Playlist, time_text
from ui.session import SessionState
from ui.widgets import CollectionHeader, TrackRow, cover_art, font, scroll_area


class PlaylistRow(QPushButton):
    """One accessible library entry, with local cover art and an open chevron."""
    def __init__(self, playlist: Playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.song_count = len(playlist.track_indices)
        self.setCheckable(True)
        self.setFixedHeight(94)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"{playlist.name}, {len(playlist.track_indices)} songs. Open playlist")
        self.setToolTip(playlist.name)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = "#30404d" if self.isDown() else (
            "#24333e" if self.isChecked() else "#1d2b36" if self.underMouse() else "#00000000")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0, 2, 0, -2), 10, 10)
        p.drawPixmap(10, 15, 64, 64, cover_art(self.playlist.colors))
        width = max(0, self.width() - 126)
        p.setFont(font(15))
        p.setPen(QColor("#f0ece6"))
        p.drawText(QRectF(90, 25, width, 23), p.fontMetrics().elidedText(
            self.playlist.name, Qt.TextElideMode.ElideRight, width))
        p.setFont(font(12))
        p.setPen(QColor("#9aa3ac"))
        p.drawText(QRectF(90, 52, width, 20), f"{self.song_count} songs")
        p.setPen(QPen(QColor("#c7a77a"), 1.4))
        x = self.width() - 22
        p.drawLine(QPointF(x - 3, 42), QPointF(x + 2, 47))
        p.drawLine(QPointF(x + 2, 47), QPointF(x - 3, 52))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#947549"), 1.5))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 3, -2, -3), 9, 9)


class PlaylistBrowser(QStackedWidget):
    """Emit intentions; MainWindow remains the owner of playback state."""
    track_requested = Signal(int)
    play_requested = Signal(int)
    # Preserve the original index signals; album-only additions have their own payload.
    extra_track_requested = Signal(object)
    extra_play_requested = Signal(object)

    def __init__(self, parent=None, state=None):
        super().__init__(parent)
        self.state = state if state is not None else SessionState(self)
        self.selected_playlist = None
        self.current_index = 0
        self.is_playing = True
        self.library_rows = []
        self.track_rows = []
        self._build_library()
        self._build_detail()
        self.state.playlist_changed.connect(self._playlist_changed)
        self.state.playlist_created.connect(self._playlist_created)

    def _build_library(self):
        self.library_page = QWidget()
        layout = QVBoxLayout(self.library_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        title = QLabel("Your Library")
        title.setObjectName("libraryTitle")
        heading.addWidget(title, 1)
        self.new_button = QPushButton("+ New playlist")
        self.new_button.setObjectName("secondaryAction")
        self.new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_button.clicked.connect(self._start_creation)
        heading.addWidget(self.new_button)
        layout.addLayout(heading)
        self.library_count = QLabel(f"{len(self.state.playlists)} playlists")
        self.library_count.setObjectName("count")
        layout.addWidget(self.library_count)
        self.composer = QFrame()
        self.composer.setObjectName("playlistComposer")
        form = QVBoxLayout(self.composer)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)
        name_label = QLabel("Playlist name")
        form.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("playlistNameInput")
        self.name_input.setPlaceholderText("A name for your collection")
        self.name_input.setAccessibleName("New playlist name")
        name_label.setBuddy(self.name_input)
        self.name_input.returnPressed.connect(self._submit_creation)
        self.name_input.textEdited.connect(lambda: self.creation_error.clear())
        form.addWidget(self.name_input)
        self.creation_error = QLabel()
        self.creation_error.setObjectName("formError")
        self.creation_error.setWordWrap(True)
        form.addWidget(self.creation_error)
        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryAction")
        self.cancel_button.clicked.connect(self._cancel_creation)
        actions.addWidget(self.cancel_button)
        self.create_button = QPushButton("Create")
        self.create_button.setObjectName("playlistPlay")
        self.create_button.clicked.connect(self._submit_creation)
        actions.addWidget(self.create_button)
        form.addLayout(actions)
        self.composer.hide()
        layout.addWidget(self.composer)
        content = QWidget()
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 4, 0)
        rows.setSpacing(8)
        self.library_rows_layout = rows
        for playlist in self.state.playlists.values():
            self._append_library_row(playlist)
        rows.addStretch()
        self.library_scroll = scroll_area(content)
        layout.addWidget(self.library_scroll, 1)
        self.addWidget(self.library_page)

    def _append_library_row(self, playlist):
        row = PlaylistRow(playlist)
        row.song_count = len(self.state.playlist_ids[playlist.id])
        row.clicked.connect(lambda checked=False: self.open_playlist(playlist))
        self.library_rows_layout.insertWidget(len(self.library_rows), row)
        self.library_rows.append(row)

    def _playlist_created(self, playlist_id):
        self._append_library_row(self.state.playlists[playlist_id])
        self.library_count.setText(f"{len(self.state.playlists)} playlists")

    def _start_creation(self):
        if not self.composer.isHidden():
            self.name_input.setFocus()
            return
        self.name_input.clear()
        self.creation_error.setText(f"Up to {self.state.PLAYLIST_NAME_LIMIT} characters.")
        self.composer.show()
        self.name_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _cancel_creation(self):
        self.composer.hide()
        self.name_input.clear()
        self.creation_error.clear()
        if self.isVisible():
            self.new_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _submit_creation(self):
        # Return/rapid clicks share one confirmation; a hidden form cannot submit twice.
        if not self.composer.isVisible():
            return
        try:
            self.state.create_playlist(self.name_input.text())
        except ValueError as error:
            self.creation_error.setText(str(error))
            self.name_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        self._cancel_creation()
        self.library_rows_layout.activate()
        self.library_scroll.ensureWidgetVisible(self.library_rows[-1])
        self.library_rows[-1].setFocus(Qt.FocusReason.OtherFocusReason)

    def hideEvent(self, event):
        self._cancel_creation()
        super().hideEvent(event)

    def _build_detail(self):
        self.detail_page = QWidget()
        layout = QVBoxLayout(self.detail_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.back_button = QPushButton("‹   Your Library")
        self.back_button.setObjectName("libraryBack")
        self.back_button.setAccessibleName("Back to Your Library")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(lambda: self.show_library(restore_focus=True))
        layout.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        header = CollectionHeader("Play playlist")
        self.cover = header.cover
        self.playlist_title = header.title
        self.playlist_title.setTextFormat(Qt.TextFormat.PlainText)
        self.playlist_count = header.metadata
        self.play_button = header.play_button
        self.play_button.clicked.connect(self._request_play)
        layout.addWidget(header)
        heading = QHBoxLayout()
        title = QLabel("Songs")
        title.setObjectName("sectionTitle")
        heading.addWidget(title, 1)
        self.total_time = QLabel()
        self.total_time.setObjectName("count")
        heading.addWidget(self.total_time)
        layout.addLayout(heading)
        content = QWidget()
        rows = QVBoxLayout(content)
        rows.setContentsMargins(0, 0, 4, 0)
        rows.setSpacing(5)
        self.detail_rows_layout = rows
        # Reuse these widgets on each visit; opening playlists never accumulates rows.
        for _ in range(max(len(item.track_indices) for item in PLAYLISTS)):
            self._add_row()
        self.empty_playlist = QLabel("No songs here yet.\nChoose Add to playlist from a song’s ··· menu.")
        self.empty_playlist.setObjectName("artist")
        self.empty_playlist.setWordWrap(True)
        self.empty_playlist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_playlist.setMinimumHeight(130)
        rows.addWidget(self.empty_playlist)
        rows.addStretch()
        self.detail_scroll = scroll_area(content)
        layout.addWidget(self.detail_scroll, 1)
        self.addWidget(self.detail_page)

    def _add_row(self):
        row = TrackRow(TRACKS[0], 0, state=self.state)
        row.show_playing_indicator = False
        row.clicked.connect(lambda checked=False: self._request_track(row))
        self.detail_rows_layout.insertWidget(len(self.track_rows), row)
        self.track_rows.append(row)

    def _request_track(self, row):
        if row.index is not None:
            self.track_requested.emit(row.index)
        else:
            self.extra_track_requested.emit(row.track)

    def _playlist_changed(self, playlist_id):
        for row in self.library_rows:
            row.song_count = len(self.state.playlist_ids[row.playlist.id])
            row.setAccessibleName(f"{row.playlist.name}, {row.song_count} songs. Open playlist")
            row.update()
        if self.selected_playlist and self.selected_playlist.id == playlist_id:
            self._refresh_detail()

    def show_library(self, reset_scroll=False, restore_focus=False):
        self._cancel_creation()
        self.setCurrentWidget(self.library_page)
        if reset_scroll:
            self.library_scroll.verticalScrollBar().setValue(0)
        for row in self.library_rows:
            row.setChecked(row.playlist == self.selected_playlist)
            if restore_focus and row.isChecked():
                row.setFocus(Qt.FocusReason.OtherFocusReason)

    def open_playlist(self, playlist):
        self._cancel_creation()
        self.selected_playlist = playlist
        self._refresh_detail()
        self.setCurrentWidget(self.detail_page)
        self.detail_scroll.verticalScrollBar().setValue(0)
        self.back_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _refresh_detail(self):
        playlist = self.selected_playlist
        tracks = [TRACKS_BY_ID[track_id] for track_id in self.state.playlist_ids[playlist.id]]
        while len(self.track_rows) < len(tracks):
            self._add_row()
        self.playlist_title.setText(playlist.name)
        self.playlist_title.setToolTip(playlist.name)
        self.playlist_count.setText(f"{len(tracks)} songs")
        self.play_button.setEnabled(bool(tracks))
        self.play_button.setVisible(bool(tracks))
        self.empty_playlist.setVisible(not tracks)
        self.play_button.setAccessibleName(f"Play playlist {playlist.name}")
        self.cover.setPixmap(cover_art(playlist.colors).scaled(
            82, 82, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        total = sum(track.seconds for track in tracks)
        self.total_time.setText(time_text(total) if tracks else "")
        for position, row in enumerate(self.track_rows):
            visible = position < len(tracks)
            row.setVisible(visible)
            if visible:
                row.track = tracks[position]
                row.index = next((i for i, track in enumerate(TRACKS) if track.id == row.track.id), None)
                row.setAccessibleName(f"{row.track.title}, {row.track.artist}")
                row.setToolTip(f"{row.track.title} · {row.track.artist}\n{row.track.album}")
        self.sync_playback(self.current_index, self.is_playing)

    def sync_playback(self, index, playing):
        self.current_index, self.is_playing = index, playing
        for row in self.track_rows:
            track = TRACKS[index] if isinstance(index, int) else index
            row.setChecked(track is not None and row.track.id == track.id)
            row.playing = playing
            row.update()

    def _request_play(self):
        if self.selected_playlist:
            ids = self.state.playlist_ids[self.selected_playlist.id]
            if ids:
                track = TRACKS_BY_ID[ids[0]]
                index = next((i for i, item in enumerate(TRACKS) if item.id == track.id), None)
                if index is not None:
                    self.play_requested.emit(index)
                else:
                    self.extra_play_requested.emit(track)
