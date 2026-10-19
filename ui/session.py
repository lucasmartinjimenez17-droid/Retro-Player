"""In-memory song collections. IDs are catalogue identities, never row positions."""
from PySide6.QtCore import QObject, Signal
from uuid import uuid4

from ui.mock_data import ALBUMS_BY_ID, INITIAL_SAVED_ALBUM_IDS, PLAYLISTS, TRACKS, TRACKS_BY_ID, Playlist


class SessionState(QObject):
    liked_changed = Signal()
    playlist_changed = Signal(str)
    queue_changed = Signal()
    saved_albums_changed = Signal()
    playlist_created = Signal(str)
    PLAYLIST_NAME_LIMIT = 80

    def __init__(self, parent=None):
        super().__init__(parent)
        self.liked_ids = []
        self.albums = ALBUMS_BY_ID
        self.saved_album_ids = list(INITIAL_SAVED_ALBUM_IDS)
        self.playlists = {playlist.id: playlist for playlist in PLAYLISTS}
        self.playlist_ids = {
            playlist.id: [TRACKS[i].id for i in playlist.track_indices]
            for playlist in PLAYLISTS
        }
        # User additions follow the existing mock upcoming catalogue.
        self.queue_ids = []

    def set_album_saved(self, album_id, saved):
        if album_id not in self.albums or (album_id in self.saved_album_ids) == saved:
            return
        if saved:
            self.saved_album_ids.append(album_id)
        else:
            self.saved_album_ids.remove(album_id)
        self.saved_albums_changed.emit()

    def create_playlist(self, name):
        name = name.strip()
        if not name:
            raise ValueError("Enter a playlist name.")
        if len(name) > self.PLAYLIST_NAME_LIMIT:
            raise ValueError(f"Use {self.PLAYLIST_NAME_LIMIT} characters or fewer.")
        playlist_id = "playlist-" + uuid4().hex
        palettes = (("#344c60", "#dfc599", "#20303e"),
                    ("#6c4955", "#e3c7a4", "#3c3f50"),
                    ("#4b6257", "#dcca9e", "#263e3d"))
        playlist = Playlist(playlist_id, name, palettes[len(self.playlists) % len(palettes)], ())
        self.playlists[playlist_id] = playlist
        self.playlist_ids[playlist_id] = []
        self.playlist_created.emit(playlist_id)
        return playlist

    def set_liked(self, track_id, liked):
        if track_id not in TRACKS_BY_ID or (track_id in self.liked_ids) == liked:
            return
        if liked:
            self.liked_ids.append(track_id)
        else:
            self.liked_ids.remove(track_id)
        self.liked_changed.emit()

    def add_to_playlist(self, playlist_id, track_id):
        tracks = self.playlist_ids[playlist_id]
        if track_id in TRACKS_BY_ID and track_id not in tracks:
            tracks.append(track_id)
            self.playlist_changed.emit(playlist_id)

    def add_to_queue(self, track_id):
        if track_id in TRACKS_BY_ID:
            self.queue_ids.append(track_id)
            self.queue_changed.emit()
