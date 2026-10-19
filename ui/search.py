"""Search entries for real mock album/artist entities, never disguised songs."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QSizePolicy

from ui.artists import artist_art
from ui.widgets import cover_art, font


class SearchResultRow(QPushButton):
    def __init__(self, entity, kind, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.kind = kind
        self.setFixedHeight(76)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Open {kind} {entity.name}")
        self.setToolTip(f"Open {kind} · {entity.name}")
        self.artwork = artist_art(entity.colors, 108) if kind == "artist" else cover_art(entity.colors)

    def matches(self, query):
        text = self.entity.name
        if self.kind == "album":
            text += " " + self.entity.artist
        return query in text.casefold()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#30404d" if self.isDown() else "#1d2b36" if self.underMouse() else "#00000000"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0, 2, 0, -2), 9, 9)
        painter.drawPixmap(8, 10, 54, 54, self.artwork)
        width = max(0, self.width() - 110)
        painter.setFont(font(14))
        painter.setPen(QColor("#f0ece6"))
        painter.drawText(QRectF(74, 14, width, 22), Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(self.entity.name, Qt.TextElideMode.ElideRight, width))
        painter.setFont(font(12))
        painter.setPen(QColor("#9aa3ac"))
        subtitle = "Artist" if self.kind == "artist" else f"Album · {self.entity.artist}"
        painter.drawText(QRectF(74, 37, width, 20),
                         painter.fontMetrics().elidedText(subtitle, Qt.TextElideMode.ElideRight, width))
        painter.setPen(QPen(QColor("#c7a77a"), 1.4))
        x = self.width() - 18
        painter.drawLine(QPointF(x - 3, 31), QPointF(x + 1, 35))
        painter.drawLine(QPointF(x + 1, 35), QPointF(x - 3, 39))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#947549"), 1.5))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(2, 3, -2, -3), 8, 8)
