"""Small playback decoration; no audio, playback state or per-row timers."""
import math

from PySide6.QtCore import QAbstractAnimation, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class PlaybackIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.phase = 0.0
        self.playing = False
        # Qt shares its animation driver. This object is created once and owned
        # by the widget, so repeated selection/navigation cannot add animations.
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(2400)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(math.tau)
        self.animation.setLoopCount(-1)
        self.animation.valueChanged.connect(self._advance)
        self.hide()

    def _advance(self, phase):
        self.phase = phase
        self.update()  # Only this 18 × 18 decoration needs repainting.

    def set_playback(self, active, playing):
        self.playing = playing
        self.setVisible(active)
        self._sync_animation()

    def _sync_animation(self):
        state = self.animation.state()
        if not self.isVisible():
            self.animation.stop()
        elif self.playing:
            if state == QAbstractAnimation.State.Paused:
                self.animation.resume()
            elif state == QAbstractAnimation.State.Stopped:
                self.animation.start()
        elif state == QAbstractAnimation.State.Running:
            self.animation.pause()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):
        self.animation.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d8b47f"))
        for i, (speed, offset) in enumerate(((1, 0.0), (2, 1.1), (1, 2.4), (3, 0.7))):
            # Integer harmonics meet smoothly at the loop boundary.
            height = 4 + 10 * (0.5 + 0.5 * math.sin(self.phase * speed + offset))
            painter.drawRoundedRect(QRectF(1 + i * 4, 17 - height, 2, height), 1, 1)
