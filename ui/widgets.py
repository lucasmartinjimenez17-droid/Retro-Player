"""Resolution-independent artwork and reusable Qt widgets."""
import math
import random
from functools import lru_cache

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor, QConicalGradient, QFont, QIcon, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap, QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget,
)

from ui.mock_data import TRACKS, Track, time_text


def font(size, family="Segoe UI", bold=False):
    result = QFont(family)
    result.setPixelSize(size)
    result.setBold(bold)
    return result


@lru_cache(maxsize=24)
def cover_art(colors: tuple[str, str, str], size=256) -> QPixmap:
    """Original geometric sleeve art, generated locally and cached."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(colors[0]))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 256, size / 256)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(colors[1]))
    p.drawEllipse(QRectF(94, 37, 115, 115))
    p.setBrush(QColor(colors[2]))
    hills = QPainterPath(QPointF(-20, 206))
    hills.cubicTo(75, 60, 132, 224, 280, 105)
    hills.lineTo(280, 280)
    hills.lineTo(-20, 280)
    p.drawPath(hills)
    p.setBrush(QColor(colors[0]))
    foreground = QPainterPath(QPointF(-10, 231))
    foreground.cubicTo(86, 135, 144, 264, 270, 172)
    foreground.lineTo(270, 270)
    foreground.lineTo(-10, 270)
    p.drawPath(foreground)
    p.setPen(QColor(colors[1]))
    p.setFont(font(13, bold=True))
    p.drawText(QRectF(22, 18, 210, 22), "THE LISTENING ROOM")
    p.setFont(font(9))
    p.drawText(QRectF(22, 226, 212, 16), "STEREO RECORDINGS       •       33⅓ RPM")
    p.end()
    return pixmap


def icon(kind: str, color="#e9ddc8", size=24) -> QIcon:
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.GlobalColor.transparent)
    pix.setDevicePixelRatio(2)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24, size / 24)
    p.setPen(QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if kind == "heart":
        heart = QPainterPath(QPointF(12, 21))
        heart.cubicTo(0, 13, 1, 3, 7, 4)
        heart.cubicTo(10, 4, 12, 7, 12, 7)
        heart.cubicTo(16, 0, 24, 5, 21, 12)
        heart.cubicTo(19, 16, 15, 19, 12, 21)
        p.drawPath(heart)
    elif kind == "search":
        p.drawEllipse(QRectF(4, 3, 12, 12))
        p.drawLine(QPointF(14, 14), QPointF(20, 20))
    elif kind == "volume":
        p.drawPolygon(QPolygonF([QPointF(3, 9), QPointF(7, 9), QPointF(12, 5),
                                 QPointF(12, 19), QPointF(7, 15), QPointF(3, 15)]))
        p.drawArc(QRectF(9, 4, 12, 16), -60 * 16, 120 * 16)
        p.drawArc(QRectF(11, 8, 5, 8), -60 * 16, 120 * 16)
    elif kind == "record":
        for radius in (9, 6, 2):
            p.drawEllipse(QPointF(12, 12), radius, radius)
    elif kind == "playing":
        for x, height in ((5, 6), (10, 15), (15, 10), (20, 18)):
            p.drawLine(QPointF(x, 21), QPointF(x, 21 - height))
    elif kind in ("playlists", "queue"):
        for y in (6, 12, 18):
            p.drawLine(QPointF(4, y), QPointF(19, y))
        if kind == "queue":
            p.drawEllipse(QPointF(9, 6), 2, 2)
            p.drawEllipse(QPointF(15, 18), 2, 2)
        else:
            p.drawLine(QPointF(19, 6), QPointF(19, 18))
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        if kind == "pause":
            p.drawRoundedRect(QRectF(6, 5, 4, 14), 1, 1)
            p.drawRoundedRect(QRectF(14, 5, 4, 14), 1, 1)
        else:
            if kind == "previous":
                p.translate(24, 0)
                p.scale(-1, 1)
            p.drawPolygon(QPolygonF([QPointF(7, 5), QPointF(18, 12), QPointF(7, 19)]))
            if kind in ("next", "previous"):
                p.drawRoundedRect(QRectF(18, 5, 2, 14), .7, .7)
    p.end()
    return QIcon(pix)


class IconButton(QPushButton):
    def __init__(self, kind, label, primary=False, parent=None):
        super().__init__(parent)
        self.primary = primary
        self.setObjectName("primaryButton" if primary else "iconButton")
        self.setFixedSize(52 if primary else 36, 52 if primary else 36)
        self.setIconSize(QSize(24, 24))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_kind(kind, label)

    def set_kind(self, kind, label):
        self.setIcon(icon(kind, "#e7be8b"))
        self.setToolTip(label)
        self.setAccessibleName(label)


class TrackRow(QPushButton):
    """Keyboard-focusable row; long text elides instead of forcing width."""
    def __init__(self, track: Track, index: int, parent=None, state=None):
        super().__init__(parent)
        self.track, self.index = track, index
        self.album_mode = False
        self.result_mode = "song"
        self.playing = True
        self.show_playing_indicator = True
        self.track_number = None
        self.setCheckable(True)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"{track.title}, {track.artist}")
        self.setToolTip(f"{track.title} · {track.artist}\n{track.album}")
        self.state = state
        self.options_button = QToolButton(self)
        self.options_button.setObjectName("trackOptions")
        self.options_button.setText("···")
        self.options_button.setFixedSize(28, 32)
        self.options_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_button.setToolTip("Song options")
        self.options_button.setAccessibleName("Song options")
        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self._populate_menu)
        self.options_button.clicked.connect(self.open_menu)
        self.options_button.setVisible(state is not None)
        if state is not None:
            state.liked_changed.connect(self.update)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.options_button.move(self.width() - 32, (self.height() - 32) // 2)

    def open_menu(self):
        if self.state is not None and self.result_mode == "song":
            self.menu.popup(self.options_button.mapToGlobal(QPoint(0, self.options_button.height())))

    def _populate_menu(self):
        for action in self.menu.actions():
            if action.menu() is not None:
                action.menu().deleteLater()
        self.menu.clear()
        # Capture the identity now: removing a favorite can immediately rebind its row.
        track_id = self.track.id
        liked = track_id in self.state.liked_ids
        action = self.menu.addAction(icon("heart"),
                                     "Unlike" if liked else "Like")
        action.triggered.connect(lambda: self.state.set_liked(track_id, not liked))
        self.playlist_menu = self.menu.addMenu(icon("playlists"), "Add to playlist")
        for playlist in self.state.playlists.values():
            included = track_id in self.state.playlist_ids[playlist.id]
            action = self.playlist_menu.addAction(playlist.name.replace("&", "&&") + ("  ·  Added" if included else ""))
            action.setData(playlist.id)
            action.setEnabled(not included)
            action.triggered.connect(
                lambda checked=False, playlist_id=playlist.id: self.state.add_to_playlist(playlist_id, track_id))
        self.menu.addSeparator()
        action = self.menu.addAction(icon("queue"), "Add to queue")
        action.triggered.connect(lambda: self.state.add_to_queue(track_id))

    def hideEvent(self, event):
        self.menu.close()
        super().hideEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Menu or (
                event.key() == Qt.Key.Key_F10 and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.open_menu()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = self.isChecked()
        background = "#30404d" if self.isDown() else (
            "#24333e" if active else "#1d2b36" if self.underMouse() else "#00000000")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(background))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0, 2, 0, -2), 9, 9)
        if active:
            p.setBrush(QColor("#d7b17e"))
            p.drawRoundedRect(QRectF(0, 20, 3, 28), 1.5, 1.5)
        if self.track_number is not None:
            p.setFont(font(12))
            p.setPen(QColor("#d7b17e" if active else "#9aa3ac"))
            p.drawText(QRectF(8, 21, 27, 25), Qt.AlignmentFlag.AlignCenter, str(self.track_number))
        elif self.result_mode == "artist":
            p.save()
            clip = QPainterPath()
            clip.addEllipse(QRectF(8, 10, 54, 54))
            p.setClipPath(clip)
            p.drawPixmap(8, 10, 54, 54, cover_art(self.track.colors))
            p.restore()
        else:
            p.drawPixmap(8, 10, 48, 48, cover_art(self.track.colors))
        text_left = 44 if self.track_number is not None else 74
        has_options = self.state is not None and self.result_mode == "song"
        trailing = 94 if has_options else 60
        width = max(0, self.width() - text_left - trailing)
        p.setFont(font(14))
        p.setPen(QColor("#f0ece6"))
        title = self.track.album if self.album_mode or self.result_mode == "album" else self.track.title
        if self.result_mode == "artist":
            title = self.track.artist
        is_song = self.result_mode == "song" and not self.album_mode
        liked = is_song and self.state is not None and self.track.id in self.state.liked_ids
        heart_size, heart_gap = 12, 6
        title_width = max(0, width - (heart_size + heart_gap if liked else 0))
        title_rect = QRectF(text_left, 14, title_width, 22)
        visible_title = p.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, title_width)
        p.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, visible_title)
        if liked:
            # Measure the elided title, not the full string or the entire text column.
            heart_x = text_left + p.fontMetrics().horizontalAdvance(visible_title) + heart_gap
            heart_y = round(title_rect.center().y() - heart_size / 2)
            icon("heart", "#d8b47f", heart_size).paint(p, heart_x, heart_y, heart_size, heart_size)
        p.setFont(font(12))
        p.setPen(QColor("#9aa3ac"))
        subtitle = "Artist" if self.result_mode == "artist" else self.track.artist
        p.drawText(QRectF(text_left, 37, width, 20),
                   p.fontMetrics().elidedText(subtitle, Qt.TextElideMode.ElideRight, width))
        offset = 32 if has_options else 0
        # Available durations always take precedence over the playback indicator.
        if is_song and self.track.seconds is not None:
            p.drawText(QRectF(self.width() - 45 - offset, 23, 37, 24),
                       Qt.AlignmentFlag.AlignCenter, time_text(self.track.seconds))
        elif is_song and active and self.playing and self.show_playing_indicator:
            icon("playing", "#d8b47f", 18).paint(p, self.width() - 33 - offset, 25, 18, 18)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#947549"), 1.5))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(2, 3, -2, -3), 8, 8)


def scroll_area(content):
    """Shared dark, vertically scrolling content for collection views."""
    content.setObjectName("playlistContent")
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(content)
    return area


class CollectionHeader(QFrame):
    """Compact cover, metadata and play action, shared by playlists and albums."""
    def __init__(self, play_label, parent=None):
        super().__init__(parent)
        self.setObjectName("playlistHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 14)
        layout.setSpacing(14)
        self.cover = QLabel()
        self.cover.setFixedSize(82, 82)
        layout.addWidget(self.cover, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        self.info_layout = info
        info.setSpacing(6)
        self.title = QLabel()
        self.title.setObjectName("playlistTitle")
        self.title.setWordWrap(True)
        self.title.setMinimumWidth(0)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.artist = QLabel()
        self.artist.setObjectName("artist")
        self.artist.setWordWrap(True)
        self.artist.hide()
        self.metadata = QLabel()
        self.metadata.setObjectName("count")
        info.addWidget(self.title)
        info.addWidget(self.artist)
        info.addWidget(self.metadata)
        self.play_button = QPushButton(play_label)
        self.play_button.setIcon(icon("play", "#18232b", 17))
        self.play_button.setObjectName("playlistPlay")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        info.addWidget(self.play_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(info, 1)


@lru_cache(maxsize=1)
def deck_texture():
    """Small deterministic local texture; cached, never generated per frame."""
    pixmap = QPixmap(160, 160)
    pixmap.fill(QColor("#1b2a37"))
    p = QPainter(pixmap)
    rng = random.Random(17)
    for _ in range(11000):
        shade = rng.choice((QColor(4, 13, 22, 65), QColor(104, 120, 130, 32)))
        p.setPen(shade)
        p.drawPoint(rng.randrange(160), rng.randrange(160))
    p.end()
    return pixmap


class WoodFrame(QFrame):
    """The surrounding wooden case continues behind the control strip."""
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 23, 23)
        p.setClipPath(clip)
        grain_color = QLinearGradient(0, 0, 0, self.height())
        for stop, color in ((0, "#a48160"), (.08, "#6d4931"), (.6, "#765137"), (.88, "#855b3a"), (1, "#3c281c")):
            grain_color.setColorAt(stop, QColor(color))
        p.fillRect(rect, grain_color)
        for y in range(0, self.height(), 3):
            p.setPen(QPen(QColor(28, 12, 5, 40 if y % 2 else 65), .8))
            line = QPainterPath(QPointF(0, y))
            line.cubicTo(self.width() * .3, y + math.sin(y) * 5,
                         self.width() * .7, y - 4, self.width(), y + 2)
            p.drawPath(line)
        p.setClipping(False)
        p.setPen(QPen(QColor("#b99774"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 23, 23)


class Turntable(QWidget):
    """Scalable illustrated deck, composed in an 820 x 650 design space."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.track = TRACKS[0]
        self.playing = True
        self.setMinimumSize(470, 410)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Tocadiscos con vinilo negro, etiqueta roja y brazo dorado")

    def set_track(self, track):
        self.track = track
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Fill the whole available surface; the physical deck keeps its proportions.
        p.setPen(QPen(QColor("#09131c"), 2))
        p.setBrush(QColor("#1b2a37"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 19, 19)
        p.save()
        surface = QPainterPath()
        surface.addRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 18, 18)
        p.setClipPath(surface)
        p.drawTiledPixmap(self.rect(), deck_texture())
        p.restore()
        scale = min(self.width() / 820, self.height() / 650)
        p.translate((self.width() - 820 * scale) / 2, (self.height() - 650 * scale) / 2)
        p.scale(scale, scale)
        center = QPointF(363, 319)
        p.setPen(Qt.PenStyle.NoPen)
        for radius in range(321, 309, -2):
            p.setBrush(QColor(0, 0, 0, 15))
            p.drawEllipse(QPointF(365, 325), radius, radius)
        wood = QLinearGradient(80, 0, 650, 650)
        for stop, color in ((0, "#b08960"), (.4, "#63442e"), (.8, "#986138"), (1, "#3f291c")):
            wood.setColorAt(stop, QColor(color))
        p.setBrush(wood)
        p.setPen(QPen(QColor("#b58c60"), 1))
        p.drawEllipse(center, 310, 310)
        metal = QLinearGradient(0, 0, 610, 610)
        for stop, color in ((0, "#cfbd9d"), (.3, "#4f524e"), (.5, "#c0bcae"), (.8, "#343c3f"), (1, "#7f8178")):
            metal.setColorAt(stop, QColor(color))
        p.setBrush(metal)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(center, 303, 303)
        sheen = QConicalGradient(center, 32)
        for stop, color in ((0, "#08090b"), (.07, "#1c1e20"), (.15, "#555658"),
                            (.22, "#252729"), (.32, "#08090a"), (.5, "#070809"),
                            (.61, "#424548"), (.69, "#242628"), (.8, "#090a0c"), (1, "#08090b")):
            sheen.setColorAt(stop, QColor(color))
        p.setBrush(sheen)
        p.drawEllipse(center, 300, 300)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for radius in range(114, 298, 2):
            p.setPen(QPen(QColor(210, 210, 211, 25 if radius % 6 else 44), .55))
            p.drawEllipse(center, radius, radius)
        for radius in (121, 155, 204, 251, 292):
            p.setPen(QPen(QColor(0, 0, 0, 140), 2))
            p.drawEllipse(center, radius, radius)
        p.setPen(QPen(QColor("#db7b79"), 1))
        p.setBrush(QColor(self.track.colors[0]))
        p.drawEllipse(center, 110, 110)
        p.setPen(QPen(QColor(255, 210, 190, 45), .7))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(center, 103, 103)
        p.drawPixmap(307, 263, 112, 112, cover_art(self.track.colors))
        p.setPen(QPen(QColor("#bb9f74"), 2))
        p.drawRect(QRectF(307, 263, 112, 112))
        brass = QLinearGradient(685, 80, 743, 104)
        for stop, color in ((0, "#5b3a1a"), (.22, "#bd9160"), (.48, "#f6dbac"), (.7, "#cba16d"), (1, "#63411e")):
            brass.setColorAt(stop, QColor(color))
        p.setPen(QPen(QColor("#65482d"), 1))
        p.setBrush(brass)
        p.drawEllipse(center, 7, 7)
        p.setBrush(QColor("#f1d4a2"))
        p.drawEllipse(QPointF(361, 316), 2, 2)
        # Speed selector at the upper left of the deck.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#080f15"))
        p.drawEllipse(QPointF(55, 74), 29, 29)
        knob = QLinearGradient(30, 43, 78, 93)
        for stop, color in ((0, "#fbdfb0"), (.45, "#b48b59"), (.55, "#f4d3a1"), (1, "#6a4623")):
            knob.setColorAt(stop, QColor(color))
        p.setBrush(knob)
        p.drawEllipse(QPointF(55, 68), 21, 21)
        p.setPen(QPen(QColor("#ead4ad"), 1.2))
        p.drawLine(QPointF(55, 40), QPointF(55, 35))
        p.setFont(font(10))
        p.drawText(QRectF(26, 111, 75, 18), "• 33     45")
        # Pivot assembly and brass counterweight.
        pivot = QPointF(728, 105)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(QPointF(732, 111), 56, 56)
        p.setPen(QPen(QColor("#53616b"), 1.5))
        p.setBrush(QColor("#263540"))
        p.drawEllipse(pivot, 50, 50)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0b151d"))
        p.drawEllipse(pivot, 36, 36)
        p.save()
        p.translate(737, 54)
        p.rotate(15)
        counterweight = QLinearGradient(-19, -22, 19, 22)
        for stop, color in ((0, "#614320"), (.35, "#d2aa72"), (.5, "#f8ddb0"), (1, "#74502c")):
            counterweight.setColorAt(stop, QColor(color))
        p.setBrush(counterweight)
        p.setPen(QPen(QColor("#5a4028"), 1))
        p.drawRoundedRect(QRectF(-19, -22, 38, 49), 7, 7)
        p.setBrush(QColor("#302215"))
        p.drawEllipse(QRectF(-19, 14, 38, 12))
        p.restore()
        knob.setStart(702, 79)
        knob.setFinalStop(754, 131)
        p.setBrush(knob)
        p.drawEllipse(pivot, 26, 26)
        for x, y in ((696, 80), (765, 90), (716, 144)):
            p.setPen(QPen(QColor("#453a2b"), 1))
            p.setBrush(QColor("#b49460"))
            p.drawEllipse(QPointF(x, y), 3, 3)
        # Curved arm and its shadow are open, unfilled paths.
        arm = QPainterPath(QPointF(721, 130))
        arm.lineTo(687, 302)
        arm.cubicTo(680, 343, 657, 367, 601, 405)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(5, 7)
        p.setPen(QPen(QColor(0, 0, 0, 120), 17, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(arm)
        p.restore()
        for width, color in ((16, "#3c2918"), (12, "#926a3d"), (8, "#dbb57e"), (3, "#f3d9ac")):
            p.setPen(QPen(QColor(color), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(arm)
        # Headshell, screws, gold cartridge and needle on the outer grooves.
        p.save()
        p.translate(598, 406)
        p.rotate(46)
        p.setBrush(QColor("#252a2c"))
        p.setPen(QPen(QColor("#9b9a8b"), 1))
        p.drawRoundedRect(QRectF(-18, -7, 36, 64), 4, 4)
        p.setBrush(counterweight)
        p.drawRect(QRectF(-16, 48, 32, 12))
        for y in (7, 35):
            p.setBrush(QColor("#d1b584"))
            p.drawEllipse(QPointF(0, y), 3, 3)
            p.setPen(QPen(QColor("#5a4830"), 1))
            p.drawLine(QPointF(-2, y), QPointF(2, y))
        p.setPen(QPen(QColor("#e6c58c"), 2))
        p.drawLine(QPointF(0, 60), QPointF(0, 65))
        p.restore()
        # Small deck engravings and a power indicator.
        p.setPen(QColor("#ddbb87"))
        p.setFont(font(11, "Georgia"))
        p.drawText(QRectF(24, 578, 220, 22), "R E T R O  P L A Y E R")
        p.setFont(font(8))
        p.setPen(QColor("#a5adb0"))
        p.drawText(QRectF(24, 602, 210, 30), "M U S I C  S O U N D S  B E T T E R\nO N  V I N Y L")
        p.setBrush(QColor("#101b24"))
        p.setPen(QPen(QColor("#d8b37b" if self.playing else "#6b6d65"), 1.5))
        p.drawEllipse(QPointF(778, 610), 17, 17)
        p.drawArc(QRectF(771, 603, 14, 14), 135 * 16, 270 * 16)
        p.drawLine(QPointF(778, 601), QPointF(778, 608))
