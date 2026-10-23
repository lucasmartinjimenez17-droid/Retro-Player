"""Resolution-independent artwork and reusable Qt widgets."""
import math
from functools import lru_cache

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPainter,
    QPainterPath, QPen, QPixmap, QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget,
)

from ui.mock_data import TRACKS, Track, time_text
from ui.playback_indicator import PlaybackIndicator
from ui.turntable_assets import ASSET_DIRECTORY, LayeredTurntable, load_artwork
from ui.turntable_motion import TurntableMotion
from ui.turntable_art import (
    ARM_BOUNDS, CENTER, deck_texture, paint_arm, paint_base, paint_label,
    paint_power, paint_record, paint_spindle, paint_surface, paint_wood, raster,
)


def font(size, family="Segoe UI", bold=False):
    result = QFont(family)
    result.setPixelSize(size)
    result.setBold(bold)
    return result


@lru_cache(maxsize=24)
def cover_art(colors: tuple[str, str, str], size=256, *, circular=False) -> QPixmap:
    """Original geometric sleeve art, generated locally and cached."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(colors[0]))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 256, size / 256)
    p.setPen(Qt.PenStyle.NoPen)
    if circular:
        # The existing mock sleeve has text in its corners. Lay out the same
        # sun/wave artwork for a round printed label so no title gets clipped.
        p.setBrush(QColor(colors[1]))
        p.drawEllipse(QRectF(105, 60, 84, 84))
        p.setBrush(QColor(colors[2]))
        wave = QPainterPath(QPointF(35, 170))
        wave.cubicTo(91, 101, 132, 184, 220, 125)
        wave.lineTo(217, 153)
        wave.cubicTo(138, 213, 102, 136, 46, 191)
        wave.closeSubpath()
        p.drawPath(wave)
        p.setPen(QColor(colors[1]))
        p.setFont(font(11))
        p.drawText(QRectF(25, 29, 206, 20), Qt.AlignmentFlag.AlignCenter, "THE LISTENING ROOM")
        p.setFont(font(8))
        p.drawText(QRectF(43, 200, 170, 15), Qt.AlignmentFlag.AlignCenter, "STEREO     ·     33⅓ RPM")
        p.drawText(QRectF(68, 224, 120, 15), Qt.AlignmentFlag.AlignCenter, "RETRO PLAYER")
        p.end()
        return pixmap
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
            if kind in ("next", "previous"):
                # Center the complete triangle + stop bar, then mirror it.
                p.translate(-1.5, 0)
            p.drawPolygon(QPolygonF([QPointF(7, 5), QPointF(18, 12), QPointF(7, 19)]))
            if kind in ("next", "previous"):
                p.drawRoundedRect(QRectF(18, 5, 2, 14), .7, .7)
    p.end()
    return QIcon(pix)


class IconButton(QPushButton):
    def __init__(self, kind, label, primary=False, parent=None):
        super().__init__(parent)
        self.primary = primary
        self.setProperty("keyboardFocus", False)
        self.setObjectName("primaryButton" if primary else "iconButton")
        self.setFixedSize(52 if primary else 36, 52 if primary else 36)
        self.setIconSize(QSize(24, 24))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_kind(kind, label)

    def set_kind(self, kind, label):
        self.setIcon(icon(kind, "#e7be8b"))
        self.setToolTip(label)
        self.setAccessibleName(label)

    def _set_keyboard_focus(self, visible):
        if self.property("keyboardFocus") != visible:
            self.setProperty("keyboardFocus", visible)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def focusInEvent(self, event):
        self._set_keyboard_focus(event.reason() in (
            Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason))
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._set_keyboard_focus(False)
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        self._set_keyboard_focus(False)
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        self._set_keyboard_focus(True)
        super().keyPressEvent(event)


class TrackRow(QPushButton):
    """Keyboard-focusable row; long text elides instead of forcing width."""
    def __init__(self, track: Track, index: int, parent=None, state=None):
        super().__init__(parent)
        self.track, self.index = track, index
        self.album_mode = False
        self.result_mode = "song"
        self._playing = True
        self.indicator = PlaybackIndicator(self)
        self.track_number = None
        self.setCheckable(True)
        self.toggled.connect(self._sync_indicator)
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
        offset = 32 if self.state is not None and self.result_mode == "song" else 0
        self.indicator.move(self.width() - 71 - offset, 25)

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, value):
        self._playing = value
        self._sync_indicator()

    def _sync_indicator(self):
        active = self.isChecked() and self.result_mode == "song" and not self.album_mode
        self.indicator.set_playback(active, self.playing)

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
        # A separate 18 px indicator column plus an 8 px gap keeps the duration,
        # heart and menu independent. Reserve it even on inactive rows.
        trailing = 120 if has_options else 86
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
        # Duration has its own column in every playback/like state.
        if is_song and self.track.seconds is not None:
            p.drawText(QRectF(self.width() - 45 - offset, 23, 37, 24),
                       Qt.AlignmentFlag.AlignCenter, time_text(self.track.seconds))
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


class WoodFrame(QFrame):
    """Walnut enclosure; one size/DPR-aware buffer, replaced on resize."""
    def paintEvent(self, event):
        key = (self.width(), self.height(), self.devicePixelRatioF())
        if getattr(self, "_wood_key", None) != key:
            self._wood = raster(*key, lambda p: paint_wood(p, self.width(), self.height()))
            self._wood_key = key
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._wood)


class Turntable(QWidget):
    """Photographic layers with a complete procedural fallback."""
    def __init__(self, parent=None, *, asset_directory=ASSET_DIRECTORY):
        super().__init__(parent)
        self.track = TRACKS[0]
        self.display_track = self.track
        self._fallback_playing = False
        self._surface_key = self._layer_density = self._label_colors = None
        self._layers = {}
        self._transport = None
        artwork, self.asset_error = load_artwork(asset_directory)
        self._asset_art = LayeredTurntable(artwork) if artwork else None
        self.motion = TurntableMotion(artwork.metadata, self) if artwork else None
        if self.motion is not None:
            self.motion.changed.connect(self._motion_repaint)
            self.motion.record_swapped.connect(self._swap_record)
        self._static_key = self._static_scene = None
        self._empty_key = self._empty_scene = None
        self.setMinimumSize(470, 410)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Tocadiscos con vinilo negro, portada central y brazo de bronce")

    @property
    def playing(self):
        return self.motion.playing if self.motion is not None else self._fallback_playing

    @playing.setter
    def playing(self, playing):
        self._fallback_playing = bool(playing)
        if self.motion is not None:
            self.motion.set_playing(playing)
        self.update()

    def set_progress(self, seconds, duration):
        if self.motion is not None:
            self.motion.set_progress(seconds, duration)

    def _motion_repaint(self):
        # The inset controls and wooden lower face do not need frame updates.
        bottom = self._transport.y() if self._transport is not None else self.height()
        self.update(0, 0, self.width(), bottom)

    def showEvent(self, event):
        super().showEvent(event)
        if self.motion is not None:
            self.motion.set_active(not self.window().isMinimized(), self.devicePixelRatioF())

    def hideEvent(self, event):
        if self.motion is not None:
            self.motion.set_active(False)
        super().hideEvent(event)

    def set_transport(self, strip):
        """Inset the existing controls into the cabinet's extended wooden face."""
        self._transport = strip
        strip.setParent(self)
        self.setMinimumHeight(522)
        self._place_transport()
        strip.show()

    def _place_transport(self):
        if self._transport is None:
            return
        if self._asset_art is not None:
            art = self._asset_art
            scale, origin = art.layout_transform(self.size(), self._transport.height())
            inset = 35
            left = round(origin.x() + inset * scale)
            right = round(origin.x() + (art.design_size[0] - inset) * scale)
            top = round(origin.y() + art.metadata["transport_split"] * scale)
            self._transport.setGeometry(left, top, right - left, self._transport.height())
        else:
            self._transport.setGeometry(12, self.height() - 112, self.width() - 24, 112)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_transport()

    def set_track(self, track):
        different = self.track.id != track.id
        self.track = track
        if different and self._asset_art is not None:
            self.motion.request_change()
        elif self._asset_art is None:
            self.display_track = track
        self.update()

    def _swap_record(self):
        self.display_track = self.track
        self.update()

    def _ensure_art(self, scale, dpr):
        # Bound memory to the current size. Moving between screens also rebuilds
        # at the new pixel density, rather than enlarging an old low-res buffer.
        surface_key = (self.width(), self.height(), dpr)
        if self._surface_key != surface_key:
            self._surface = raster(*surface_key, lambda p: paint_surface(p, self.width(), self.height()))
            self._surface_key = surface_key
        # Half-step buckets avoid rebuilding the expensive groove/metal layers
        # for every pixel of a live resize. Always render above screen density.
        density = max(1.5, math.ceil(scale * dpr * 2) / 2)
        if self._layer_density != density:
            self._layers = {
                "base": raster(820, 650, density, paint_base),
                "record": raster(606, 606, density, paint_record),
                # Supersample the narrow metallic highlights at small sizes;
                # otherwise adjacent subpixel ribbons can produce moiré.
                "arm": raster(ARM_BOUNDS.width(), ARM_BOUNDS.height(), max(2, density), paint_arm),
            }
            self._layer_density = density
            self._label_colors = None
        if self._label_colors != self.track.colors:
            self._layers["label"] = raster(224, 224, density, lambda p: paint_label(
                p, self.track.colors, cover_art(self.track.colors)))
            self._label_colors = self.track.colors

    @staticmethod
    def _draw_layer(painter, rect, pixmap):
        painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))

    def paintEvent(self, event):
        if self._asset_art is not None:
            art = self._asset_art
            transport_height = self._transport.height() if self._transport is not None else 0
            scale, origin = art.layout_transform(self.size(), transport_height)
            art.prepare(scale, self.devicePixelRatioF(), cover_art(self.display_track.colors, 512, circular=True))
            dpr = self.devicePixelRatioF()
            key = (self.width(), self.height(), dpr, art.density, transport_height)
            if key != self._static_key:
                scene = QPixmap(math.ceil(self.width() * dpr), math.ceil(self.height() * dpr))
                scene.setDevicePixelRatio(dpr)
                scene.fill(QColor(art.metadata["background"]))
                p = QPainter(scene)
                p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
                p.translate(origin)
                p.scale(scale, scale)
                art.paint_static(p, transport_height / scale)
                p.end()
                self._static_scene, self._static_key = scene, key
                if self.motion is not None:
                    self.motion.set_active(self.motion.active, dpr)
            painter = QPainter(self)
            painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                                   QPainter.RenderHint.SmoothPixmapTransform)
            # Match the shell outside the single wooden silhouette, including
            # standalone widget captures where Qt does not paint the parent.
            fading = self.motion.record_opacity < 1
            if fading and self._empty_key != key:
                empty = QPixmap(self._static_scene.size())
                empty.setDevicePixelRatio(dpr)
                empty.fill(QColor(art.metadata["background"]))
                p = QPainter(empty)
                p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
                p.translate(origin)
                p.scale(scale, scale)
                art.paint_static(p, transport_height / scale, include_record=False)
                p.end()
                self._empty_scene, self._empty_key = empty, key
            painter.drawPixmap(0, 0, self._empty_scene if fading else self._static_scene)
            painter.translate(origin)
            painter.scale(scale, scale)
            if fading:
                art.paint_fading_record(painter, self.motion.record_angle, self.motion.record_opacity)
            art.paint_moving(painter, self.motion.record_angle, self.motion.arm_angle,
                             self.motion.arm_lift, include_record=not fading)
            return
        available_height = self.height() - (112 if self._transport is not None else 0)
        scale = min(self.width() / 820, available_height / 650)
        self._ensure_art(scale, self.devicePixelRatioF())
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                               QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self._surface)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(4, 4, -4, -4), 15, 15)
        painter.setClipPath(clip)
        painter.translate((self.width() - 820 * scale) / 2, (available_height - 650 * scale) / 2)
        painter.scale(scale, scale)
        self._draw_layer(painter, QRectF(0, 0, 820, 650), self._layers["base"])
        # Future rotation can wrap record/label around CENTER without rotating
        # the platter, fixed spindle or arm. No transforms are animated yet.
        self._draw_layer(painter, QRectF(CENTER.x() - 303, CENTER.y() - 303, 606, 606), self._layers["record"])
        self._draw_layer(painter, QRectF(CENTER.x() - 112, CENTER.y() - 112, 224, 224), self._layers["label"])
        paint_spindle(painter)
        self._draw_layer(painter, ARM_BOUNDS, self._layers["arm"])
        paint_power(painter, self.playing)
