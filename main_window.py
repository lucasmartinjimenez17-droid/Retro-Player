"""RetroPlayer V1: offline view and local mock state, independent of Spotify."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QPushButton, QScrollArea, QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from ui.mock_data import ALBUMS, ARTISTS, TRACKS, TRACKS_BY_ID, time_text
from ui.artists import ArtistProfile
from ui.search import SearchResultRow
from ui.session import SessionState
from ui.liked import LikedSongs
from ui.albums import AlbumBrowser
from ui.playlists import PlaylistBrowser
from ui.widgets import IconButton, TrackRow, Turntable, cover_art, icon


def label(text, name):
    widget = QLabel(text)
    widget.setObjectName(name)
    return widget


class MainWindow(QMainWindow):
    playback_toggled = Signal(bool)
    track_selected = Signal(object)
    seek_requested = Signal(int)
    volume_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.state = SessionState(self)
        self.queue_rows = []
        self.current_index = 0
        self.is_playing = True
        self.section = "Search"
        self.search_route = ("results", None)
        self.search_history = []
        self.navigation_revision = 0
        self.setWindowTitle("Retro Player")
        self.setWindowIcon(icon("record"))
        self.resize(1400, 900)
        self.setMinimumSize(1120, 760)
        self.setStyleSheet((Path(__file__).parent / "ui" / "style.qss").read_text(encoding="utf-8"))
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(22, 0, 22, 20)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(8, 16, 8, 16)
        mark = QLabel()
        mark.setPixmap(icon("record", "#dfbd8d", 27).pixmap(27, 27))
        header.addWidget(mark)
        header.addSpacing(7)
        header.addWidget(label("RETRO PLAYER", "brand"))
        header.addStretch()
        self.status = label("DEMO SESSION", "micro")
        header.addWidget(self.status)
        layout.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(22)
        body.addWidget(self._player(), 7)
        body.addWidget(self._sidebar(), 4)
        layout.addLayout(body, 1)
        self._show_track(0, initial=True)

    def _player(self):
        # The turntable asset already owns the wooden enclosure. A second wood
        # frame around it and the transport created the nested-box appearance.
        player = QFrame()
        player.setObjectName("playerArea")
        layout = QVBoxLayout(player)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(0)
        self.turntable = Turntable()
        layout.addWidget(self.turntable, 1)
        strip = QFrame()
        strip.setObjectName("controlStrip")
        strip.setFixedHeight(112)
        controls = QHBoxLayout(strip)
        controls.setContentsMargins(12, 12, 14, 12)
        controls.setSpacing(12)
        self.sleeve = QLabel()
        self.sleeve.setFixedSize(60, 60)
        controls.addWidget(self.sleeve)
        song = QVBoxLayout()
        song.setSpacing(6)
        song.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.song_title = label("", "songTitle")
        self.song_title.setWordWrap(True)
        self.song_title.setMinimumWidth(95)
        self.song_title.setMaximumWidth(160)
        self.song_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.artist = label("", "artist")
        self.artist.setWordWrap(True)
        self.artist.setMaximumWidth(160)
        song.addWidget(self.song_title)
        song.addWidget(self.artist)
        controls.addLayout(song, 2)
        transport = QVBoxLayout()
        transport.setSpacing(5)
        buttons = QHBoxLayout()
        buttons.setSpacing(14)
        buttons.addStretch()
        self.previous_button = IconButton("previous", "Canción anterior")
        self.previous_button.clicked.connect(lambda: self._step(-1))
        self.play_button = IconButton("pause", "Pausar demo", primary=True)
        self.play_button.clicked.connect(self._toggle_playback)
        self.next_button = IconButton("next", "Canción siguiente")
        self.next_button.clicked.connect(lambda: self._step(1))
        for button in (self.previous_button, self.play_button, self.next_button):
            buttons.addWidget(button)
        buttons.addStretch()
        transport.addLayout(buttons)
        timeline = QHBoxLayout()
        timeline.setSpacing(8)
        self.elapsed = label("", "time")
        self.elapsed.setFixedWidth(28)
        self.duration = label("", "time")
        self.duration.setFixedWidth(28)
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setMinimumWidth(100)
        self.progress.setAccessibleName("Progreso de reproducción de ejemplo")
        self.progress.setToolTip("Posición de ejemplo · sin audio")
        self.progress.valueChanged.connect(self._seek)
        timeline.addWidget(self.elapsed)
        timeline.addWidget(self.progress, 1)
        timeline.addWidget(self.duration)
        transport.addLayout(timeline)
        controls.addLayout(transport, 5)
        volume_group = QVBoxLayout()
        volume_group.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        volume_group.setSpacing(8)
        volume_line = QHBoxLayout()
        volume_line.setSpacing(8)
        speaker = QLabel()
        speaker.setPixmap(icon("volume", "#dfbd8d", 20).pixmap(20, 20))
        volume_line.addWidget(speaker)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(65)
        self.volume.setFixedWidth(76)
        self.volume.setAccessibleName("Volumen de ejemplo")
        self.volume.setToolTip("Volumen de ejemplo · sin salida de audio")
        self.volume_value = label("65%", "time")
        self.volume_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.volume.valueChanged.connect(self._volume_changed)
        volume_line.addWidget(self.volume)
        volume_group.addLayout(volume_line)
        volume_group.addWidget(self.volume_value)
        controls.addLayout(volume_group)
        self.turntable.set_transport(strip)
        return player

    def _sidebar(self):
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setMinimumWidth(350)
        panel.setMaximumWidth(460)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 4, 18, 14)
        layout.setSpacing(18)
        tabs = QHBoxLayout()
        tabs.setSpacing(0)
        self.tabs = QButtonGroup(self)
        for title in ("Search", "Playlists", "Albums", "Queue", "Liked"):
            button = QPushButton(title)
            button.setToolTip("Liked Songs" if title == "Liked" else title)
            button.setAccessibleName("Liked Songs" if title == "Liked" else title)
            button.setObjectName("tab")
            button.setCheckable(True)
            button.setChecked(title == "Search")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.tabs.addButton(button)
            tabs.addWidget(button)
        self.tabs.buttonClicked.connect(self._change_section)
        layout.addLayout(tabs)
        self.sidebar_pages = QStackedWidget()
        self.catalog_page = QWidget()
        catalog_layout = QVBoxLayout(self.catalog_page)
        catalog_layout.setContentsMargins(0, 0, 0, 0)
        catalog_layout.setSpacing(18)
        self.search_box = QFrame()
        self.search_box.setObjectName("searchBox")
        search_layout = QHBoxLayout(self.search_box)
        search_layout.setContentsMargins(14, 0, 10, 0)
        search_icon = QLabel()
        search_icon.setPixmap(icon("search", "#a5adb4", 20).pixmap(20, 20))
        search_layout.addWidget(search_icon)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search songs, artists, albums")
        self.search.setAccessibleName("Buscar en el catálogo de ejemplo")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_rows)
        search_layout.addWidget(self.search)
        catalog_layout.addWidget(self.search_box)
        scroll = QScrollArea()
        self.catalog_scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("listContent")
        self.rows_layout = QVBoxLayout(content)
        self.rows_layout.setContentsMargins(0, 0, 3, 0)
        self.rows_layout.setSpacing(5)
        self.top_heading = label("Top Results", "sectionTitle")
        self.rows_layout.addWidget(self.top_heading)
        song_result = TrackRow(TRACKS[0], 0, state=self.state)
        song_result.setFixedHeight(76)
        song_result.clicked.connect(lambda checked=False: self._show_track(0))
        self.rows_layout.addWidget(song_result)
        self.search_result_rows = []
        for kind, entities in (("album", ALBUMS), ("artist", ARTISTS)):
            for entity in entities:
                row = SearchResultRow(entity, kind)
                row.clicked.connect(lambda checked=False, item=row:
                                    self._open_search_result(item.kind, item.entity.id))
                self.search_result_rows.append(row)
                self.rows_layout.addWidget(row)
        self.top_rows = [song_result]
        self.heading_widget = QWidget()
        heading = QHBoxLayout(self.heading_widget)
        heading.setContentsMargins(0, 13, 0, 5)
        self.section_title = label("Songs", "sectionTitle")
        self.result_count = label("6 tracks", "count")
        heading.addWidget(self.section_title, 1)
        heading.addWidget(self.result_count)
        self.rows_layout.addWidget(self.heading_widget)
        self.rows = []
        for index, track in enumerate(TRACKS):
            row = TrackRow(track, index, state=self.state)
            row.clicked.connect(lambda checked=False, i=index: self._show_track(i))
            self.rows_layout.addWidget(row)
            self.rows.append(row)
        self.empty = label("No records found.\nTry another song, artist or album.", "artist")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        self.empty.hide()
        self.rows_layout.addWidget(self.empty)
        self.rows_layout.addStretch()
        scroll.setWidget(content)
        catalog_layout.addWidget(scroll, 1)
        self.sidebar_pages.addWidget(self.catalog_page)
        self.playlists = PlaylistBrowser(state=self.state)
        self.playlists.track_requested.connect(self._show_track)
        self.playlists.extra_track_requested.connect(self._show_track)
        self.playlists.play_requested.connect(self._play_collection)
        self.playlists.extra_play_requested.connect(self._play_collection)
        self.sidebar_pages.addWidget(self.playlists)
        self.albums = AlbumBrowser(state=self.state)
        self.albums.track_requested.connect(self._show_track)
        self.albums.play_requested.connect(self._play_collection)
        self.albums.back_requested.connect(self._search_back)
        self.sidebar_pages.addWidget(self.albums)
        self.liked = LikedSongs(self.state)
        self.liked.track_requested.connect(self._show_track)
        self.sidebar_pages.addWidget(self.liked)
        self.state.queue_changed.connect(self._refresh_queue)
        self.artist_profile = ArtistProfile(self.state)
        self.artist_profile.track_requested.connect(self._show_track)
        self.artist_profile.album_requested.connect(lambda album_id: self._open_search_result("album", album_id))
        self.artist_profile.back_requested.connect(self._search_back)
        self.sidebar_pages.addWidget(self.artist_profile)
        layout.addWidget(self.sidebar_pages, 1)
        return panel

    def _show_track(self, selection, initial=False):
        # Existing callers use a catalogue index; Albums supplies the same Track model.
        track = TRACKS[selection] if isinstance(selection, int) else selection
        self.current_track = track
        self.current_index = next((i for i, item in enumerate(TRACKS) if item == track), None)
        self.turntable.set_track(track)
        self.sleeve.setPixmap(cover_art(track.colors).scaled(
            60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.song_title.setText(track.title)
        self.artist.setText(track.artist)
        self.song_title.setToolTip(f"{track.title} · {track.album}")
        self.duration.setText(time_text(track.seconds))
        self.progress.blockSignals(True)
        self.progress.setRange(0, track.seconds)
        self.progress.setValue(102 if initial else 0)
        self.progress.blockSignals(False)
        self.elapsed.setText(time_text(self.progress.value()))
        for row in self.rows:
            row.setChecked(row.track.id == track.id)
        for row in self.top_rows:
            row.setChecked(row.track.id == track.id)
        self.playlists.sync_playback(self.current_track, self.is_playing)
        self.albums.sync_playback(track, self.is_playing)
        self.liked.sync_playback(track, self.is_playing)
        self.artist_profile.sync_playback(track, self.is_playing)
        self._sync_queue_selection()
        self._filter_rows()
        if not initial:
            self.track_selected.emit(track)

    def _step(self, offset):
        if self.current_index is None:
            self._show_track(0 if offset > 0 else len(TRACKS) - 1)
        else:
            self._show_track((self.current_index + offset) % len(TRACKS))

    def _play_collection(self, first_track):
        self._show_track(first_track)
        if not self.is_playing:
            self._toggle_playback()

    def _toggle_playback(self):
        self.is_playing = not self.is_playing
        self.play_button.set_kind("pause" if self.is_playing else "play",
                                  "Pausar demo" if self.is_playing else "Reanudar demo")
        self.status.setText("DEMO SESSION" if self.is_playing else "DEMO PAUSED")
        self.turntable.playing = self.is_playing
        self.turntable.update()
        for row in [*self.rows, *self.top_rows]:
            row.playing = self.is_playing
            row.update()
        self.playlists.sync_playback(self.current_track, self.is_playing)
        self.albums.sync_playback(self.current_track, self.is_playing)
        self.liked.sync_playback(self.current_track, self.is_playing)
        self.artist_profile.sync_playback(self.current_track, self.is_playing)
        self._sync_queue_selection()
        self.playback_toggled.emit(self.is_playing)

    def _seek(self, seconds):
        self.elapsed.setText(time_text(seconds))
        self.seek_requested.emit(seconds)

    def _volume_changed(self, value):
        self.volume_value.setText(f"{value}%")
        self.volume_changed.emit(value)

    def _change_section(self, button):
        for menu in self.findChildren(QMenu):
            menu.close()
        self.navigation_revision += 1
        self.search_history.clear()
        self.search_route = ("results", None)
        self.section = button.text()
        if self.section == "Playlists":
            self.playlists.show_library(reset_scroll=True)
            self.sidebar_pages.setCurrentWidget(self.playlists)
            return
        if self.section == "Albums":
            self.albums.show_library(reset_scroll=True)
            self.sidebar_pages.setCurrentWidget(self.albums)
            return
        if self.section == "Liked":
            self.sidebar_pages.setCurrentWidget(self.liked)
            return
        self.sidebar_pages.setCurrentWidget(self.catalog_page)
        self.search_box.setVisible(self.section == "Search")
        self.section_title.setText({"Search": "Songs",
                                    "Queue": "Up next"}[self.section])
        self._filter_rows()

    def _filter_rows(self):
        if self.section in ("Playlists", "Albums", "Liked"):
            return
        query = self.search.text().strip().casefold() if self.section == "Search" else ""
        count = 0
        top = TRACKS[0]
        show_top = self.section == "Search" and query in f"{top.title} {top.artist} {top.album}".casefold()
        self.top_rows[0].setVisible(show_top)
        visible_entities = 0
        for row in self.search_result_rows:
            featured = row.entity.id in (ALBUMS[0].id, ARTISTS[0].id)
            visible = self.section == "Search" and row.matches(query) and (bool(query) or featured)
            row.setVisible(visible)
            visible_entities += int(visible)
        self.top_heading.setVisible(show_top or visible_entities > 0)
        ordered_rows = self.rows
        if self.section == "Queue" and self.current_index is not None:
            ordered_rows = self.rows[self.current_index + 1:] + self.rows[:self.current_index]
        ordered_rows = ordered_rows + self.queue_rows
        start = self.rows_layout.indexOf(self.heading_widget) + 1
        for position, row in enumerate(ordered_rows):
            self.rows_layout.insertWidget(start + position, row)
        for row in self.rows:
            track = row.track
            visible = query in f"{track.title} {track.artist} {track.album}".casefold()
            if self.section == "Queue":
                visible = visible and row.index != self.current_index
            row.album_mode = False
            row.setVisible(visible)
            row.update()
            count += int(visible)
        for row in self.queue_rows:
            track = row.track
            visible = self.section == "Queue" and query in f"{track.title} {track.artist} {track.album}".casefold()
            row.setVisible(visible)
            count += int(visible)
        self.result_count.setText(f"{count} tracks")
        self.empty.setVisible(count == 0 and not show_top and visible_entities == 0)

    def _refresh_queue(self):
        while len(self.queue_rows) < len(self.state.queue_ids):
            track = TRACKS_BY_ID[self.state.queue_ids[len(self.queue_rows)]]
            row = TrackRow(track, None, state=self.state)
            row.clicked.connect(lambda checked=False, item=row: self._show_track(item.track))
            self.rows_layout.insertWidget(self.rows_layout.indexOf(self.empty), row)
            row.hide()
            self.queue_rows.append(row)
        self._sync_queue_selection()
        self._filter_rows()

    def _sync_queue_selection(self):
        for row in self.queue_rows:
            row.setChecked(row.track.id == self.current_track.id)
            row.playing = self.is_playing
            row.update()

    def _search_scroll(self):
        if self.search_route[0] == "artist":
            return self.artist_profile.scroll
        if self.search_route[0] == "album":
            return self.albums.detail_scroll
        return self.catalog_scroll

    def _open_search_result(self, kind, entity_id):
        if self.section != "Search":
            return
        self.search_history.append((self.search_route,
                                    self._search_scroll().verticalScrollBar().value(),
                                    self.focusWidget()))
        self.navigation_revision += 1
        self.search_route = (kind, entity_id)
        self._display_search_route(entering=True)
        back_button = self.artist_profile.back_button if kind == "artist" else self.albums.back_button
        self._restore_search_position(0, back_button)

    def _display_search_route(self, entering=False):
        kind, entity_id = self.search_route
        if kind == "album":
            origin = self.search_history[-1][0][0] if self.search_history else "results"
            self.albums.open_album(entity_id, back_label="Artist profile" if origin == "artist" else "Search results")
            self.sidebar_pages.setCurrentWidget(self.albums)
        elif kind == "artist":
            self.sidebar_pages.setCurrentWidget(self.artist_profile)
            if entering or self.artist_profile.artist_id != entity_id:
                self.artist_profile.open_artist(entity_id)
        else:
            self.sidebar_pages.setCurrentWidget(self.catalog_page)

    def _search_back(self):
        if self.section != "Search" or not self.search_history:
            return
        self.search_route, scroll_position, focused = self.search_history.pop()
        self.navigation_revision += 1
        self._display_search_route()
        self._restore_search_position(scroll_position, focused)

    def _restore_search_position(self, scroll_position, focused):
        revision = self.navigation_revision

        def restore():
            # Ignore a deferred restore if the user has already navigated elsewhere.
            if self.section == "Search" and self.navigation_revision == revision:
                if focused is not None and focused.isVisible():
                    focused.setFocus(Qt.FocusReason.OtherFocusReason)
                self._search_scroll().verticalScrollBar().setValue(scroll_position)

        QTimer.singleShot(0, self, restore)
