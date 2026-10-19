"""Demo catalogue, independent of Spotify and authentication."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    album: str
    seconds: int
    colors: tuple[str, str, str]
    album_id: str
    id: str


TRACKS = (
    Track("Midnight in Blue", "The Velvet Hours", "After the Last Light", 258,
          ("#a7353e", "#e5bc7c", "#304f4b"), "after-the-last-light", "song-249e857f56da"),
    Track("A Sunday Kind of Love", "June & the Satellites", "Slow Mornings", 224,
          ("#b65f43", "#efd1a3", "#763a32"), "slow-mornings", "song-0008a2a77325"),
    Track("Where the Light Goes", "Arthur Miles", "Golden", 306,
          ("#b5b09a", "#f2dfad", "#485c4c"), "golden", "song-3ce3bca5fa58"),
    Track("Softly, Slowly", "The Velvet Hours", "After the Last Light", 197,
          ("#a7353e", "#e5bc7c", "#304f4b"), "after-the-last-light", "song-e6ee0e9eb0d8"),
    Track("Small Hours", "Nina Shore", "Ocean Room", 241,
          ("#5f8186", "#d9cab1", "#203c50"), "ocean-room", "song-ac4d5912f9e0"),
    Track("Stay a Little Longer", "Louis & June", "Letters from Home", 283,
          ("#6a5145", "#cbb188", "#937762"), "letters-from-home", "song-6e38a6e31afc"),
)


@dataclass(frozen=True)
class Playlist:
    """Local identity, cover palette and ordered references into the catalogue."""
    id: str
    name: str
    colors: tuple[str, str, str]
    track_indices: tuple[int, ...]


PLAYLISTS = (
    Playlist("midnight-sessions", "Midnight Sessions", ("#273b52", "#d6b183", "#66547d"),
             (0, 4, 3, 5, 1, 2)),
    Playlist("slow-sunday", "Slow Sunday", ("#a46b4d", "#f1d5a0", "#5d644f"),
             (1, 3, 5, 0)),
    Playlist("golden-hour", "Golden Hour", ("#a38445", "#f3dfaa", "#714c38"),
             (2, 1, 5, 4, 0)),
    Playlist("blue-notes", "Blue Notes", ("#244a5a", "#a9c2bb", "#182d43"),
             (4, 0, 3)),
    Playlist("letters-from-home", "Letters from Home", ("#714454", "#e3c3ac", "#4e5860"),
             (5, 2)),
)


@dataclass(frozen=True)
class Album:
    id: str
    name: str
    artist: str
    year: int | None
    colors: tuple[str, str, str]
    tracks: tuple[Track, ...]


def _mock_album(seed_index: int, year: int, entries: tuple[tuple[str, str], ...]) -> Album:
    """Keep the six-track demo catalogue intact; add tracks to its albums only."""
    seed = TRACKS[seed_index]
    existing = tuple(track for track in TRACKS if track.album_id == seed.album_id)
    additional = tuple(
        Track(title, seed.artist, seed.album, 180 + (seed.seconds + index * 29) % 170,
              seed.colors, seed.album_id, track_id)
        for index, (track_id, title) in enumerate(entries)
    )
    return Album(seed.album_id, seed.album, seed.artist, year, seed.colors, existing + additional)


ALBUMS = (
    _mock_album(0, 2023, (("song-eb8981d54691", "Last Train Home"), ("song-dd2a3da04438", "A Window Left Open"), ("song-3ae3ae7ffe72", "Velvet Skies"),
                         ("song-bcc5a83e79ff", "The Quiet Between Two Cities"), ("song-c11edf6c6d5b", "Blue Hour Interlude"),
                         ("song-19e0bd059f2f", "Nothing Left to Say"), ("song-8f1871130491", "Under the Streetlights"),
                         ("song-dd2bd34927d6", "When the Whole World Falls Asleep"), ("song-662dabd7d032", "One More Night"), ("song-110d42df5e97", "First Light"))),
    _mock_album(1, 2021, (("song-186e221776ae", "Coffee at Nine"), ("song-ba959ffc4ab8", "Curtains in the Breeze"), ("song-60d2a934e6b6", "Paper Birds"), ("song-bf17997e2b46", "Sunday Again"))),
    _mock_album(2, 2024, (("song-528ead8af455", "Amber"), ("song-e3c80e39a8e4", "Wildflowers"), ("song-7fc392f45191", "The Long Way to the River"),
                         ("song-96ec6684e52a", "Summer Dust"), ("song-9492f4d51d63", "Everything in Its Own Time"), ("song-edf2d694163f", "Evening Sun"))),
    _mock_album(4, 2022, (("song-ca05adf69877", "Saltwater"), ("song-04e86102c684", "The Far Shore"), ("song-768a8b418020", "Tides"))),
    _mock_album(5, 2020, (("song-f78c324e49c5", "Postmarked June"), ("song-4e208b18d1e8", "An Empty Station"), ("song-d793a20ed9be", "The House on the Hill"),
                         ("song-bf38d4226b55", "Things We Never Said"), ("song-093aebdb66b0", "Home Before Dark"))),
    Album("moonlit-water", "Moonlit Water", "Nina Shore", 2025,
          ("#354d68", "#d7c5a1", "#182d43"), (
              Track("After the Tide", "Nina Shore", "Moonlit Water", 232,
                    ("#354d68", "#d7c5a1", "#182d43"), "moonlit-water", "song-8e1f94d076b3"),
              Track("Silver on the Water", "Nina Shore", "Moonlit Water", 278,
                    ("#354d68", "#d7c5a1", "#182d43"), "moonlit-water", "song-a37c409e6182"),
              Track("Before the Morning", "Nina Shore", "Moonlit Water", 205,
                    ("#354d68", "#d7c5a1", "#182d43"), "moonlit-water", "song-f620b1593e48"),
          )),
)
ALBUMS_BY_ID = {album.id: album for album in ALBUMS}
TRACKS_BY_ID = {track.id: track for album in ALBUMS for track in album.tracks}
INITIAL_SAVED_ALBUM_IDS = (
    "after-the-last-light", "slow-mornings", "golden", "ocean-room", "letters-from-home",
)


@dataclass(frozen=True)
class Artist:
    id: str
    name: str
    colors: tuple[str, str, str]
    album_ids: tuple[str, ...]
    track_ids: tuple[str, ...]


def _mock_artist(artist_id, album_ids):
    albums = [ALBUMS_BY_ID[album_id] for album_id in album_ids]
    return Artist(artist_id, albums[0].artist, albums[0].colors, album_ids,
                  tuple(dict.fromkeys(track.id for album in albums for track in album.tracks)))


ARTISTS = (
    _mock_artist("artist-velvet-hours", ("after-the-last-light",)),
    _mock_artist("artist-june-satellites", ("slow-mornings",)),
    _mock_artist("artist-arthur-miles", ("golden",)),
    _mock_artist("artist-nina-shore", ("ocean-room", "moonlit-water")),
    _mock_artist("artist-louis-june", ("letters-from-home",)),
    # A discoverable mock profile with no releases; do not manufacture membership.
    Artist("artist-listening-room", "The Listening Room", ("#344554", "#d8bd94", "#1e303d"), (), ()),
)
ARTISTS_BY_ID = {artist.id: artist for artist in ARTISTS}


def time_text(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"
