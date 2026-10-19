"""Saved songs for this session, using the same song rows and actions."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.mock_data import TRACKS_BY_ID
from ui.widgets import TrackRow, icon, scroll_area


class LikedSongs(QWidget):
    track_requested = Signal(object)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.rows = []
        self.current_track = None
        self.is_playing = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        title = QLabel("Liked Songs")
        title.setObjectName("libraryTitle")
        heading.addWidget(title, 1)
        self.count = QLabel()
        self.count.setObjectName("count")
        heading.addWidget(self.count)
        layout.addLayout(heading)
        content = QWidget()
        self.rows_layout = QVBoxLayout(content)
        self.rows_layout.setContentsMargins(0, 0, 4, 0)
        self.rows_layout.setSpacing(5)
        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setContentsMargins(16, 60, 16, 50)
        heart = QLabel()
        heart.setPixmap(icon("heart", "#c7a77a", 40).pixmap(40, 40))
        heart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(heart)
        message = QLabel("Keep your favorites close")
        message.setObjectName("sectionTitle")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(message)
        hint = QLabel("Save a song from its ··· menu.\nYour collection starts here.")
        hint.setObjectName("artist")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        empty_layout.addWidget(hint)
        self.rows_layout.addWidget(self.empty)
        self.rows_layout.addStretch()
        self.scroll = scroll_area(content)
        layout.addWidget(self.scroll, 1)
        state.liked_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        tracks = [TRACKS_BY_ID[track_id] for track_id in self.state.liked_ids]
        while len(self.rows) < len(tracks):
            row = TrackRow(tracks[len(self.rows)], None, state=self.state)
            row.show_playing_indicator = False
            row.clicked.connect(lambda checked=False, item=row: self.track_requested.emit(item.track))
            self.rows_layout.insertWidget(len(self.rows), row)
            self.rows.append(row)
        for position, row in enumerate(self.rows):
            row.setVisible(position < len(tracks))
            if position < len(tracks):
                row.track = tracks[position]
                row.setAccessibleName(f"{row.track.title}, {row.track.artist}")
                row.setToolTip(f"{row.track.title} · {row.track.artist}\n{row.track.album}")
        self.count.setText(f"{len(tracks)} {'song' if len(tracks) == 1 else 'songs'}")
        self.empty.setVisible(not tracks)
        self.sync_playback(self.current_track, self.is_playing)

    def sync_playback(self, track, playing):
        self.current_track, self.is_playing = track, playing
        for row in self.rows:
            row.setChecked(track is not None and row.track.id == track.id)
            row.playing = playing
            row.update()
