"""Reproducible native Qt record-exchange frames, without audio or network."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if "--hidpi" in sys.argv:
    os.environ["QT_SCALE_FACTOR"] = "2"

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from shiboken6 import delete
from main_window import MainWindow
from ui.widgets import cover_art, deck_texture


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    w = MainWindow()
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    w.show()
    app.processEvents()
    d, m = w.turntable, w.turntable.motion
    m.set_active(False)
    m.advance(1.2)
    output = Path(__file__).resolve().parents[1] / "docs" / "record-change"
    output.mkdir(exist_ok=True)
    suffix = "-2x" if "--hidpi" in sys.argv else ""
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        w.resize(width, height)
        app.processEvents()
        w.next_button.click()
        m.advance(1)
        app.processEvents()
        w.grab().save(str(output / f"empty-{width}x{height}{suffix}.png"))
        m.advance(.8)
        app.processEvents()
        w.grab().save(str(output / f"return-{width}x{height}{suffix}.png"))
        m.advance(.3)
    if not suffix:
        w.resize(1120, 760)
        app.processEvents()
        frames = output / "frames"
        frames.mkdir(exist_ok=True)
        captions = {"idle": "PLAY" , "lift": "LEVANTAR AGUJA", "withdraw": "APARTAR BRAZO",
                    "remove": "RETIRAR DISCO", "empty": "PLATO VACÍO", "insert": "COLOCAR NUEVO DISCO",
                    "return": "ENTRAR AL SURCO", "lower": "BAJAR AGUJA"}
        sample_frames = (15, 21, 33, 42, 45, 54, 66, 75)
        board = QPixmap(1280, 4 * 620)
        board.fill(QColor("#101b25"))
        bp = QPainter(board)
        states = []
        for i in range(210):
            if i == 15:
                w.next_button.click()
            elif i == 105:
                w.play_button.click()
                w.previous_button.click()
            elif i == 180:
                w.play_button.click()
            caption = captions[m.phase] if m.changing or w.is_playing else "DISCO LISTO · PAUSA"
            picture = QPixmap(640, 620)
            picture.fill(QColor("#101b25"))
            p = QPainter(picture)
            p.setPen(QColor("#e7c99d"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(12, 24, f"{i / 30:.2f} s · {caption}")
            shot = d.grab().scaled(640, 580, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((640 - shot.width()) // 2, 38, shot)
            p.end()
            picture.save(str(frames / f"{i:03d}.webp"), "WEBP", 92)
            if i in sample_frames:
                n = sample_frames.index(i)
                bp.drawPixmap((n % 2) * 640, (n // 2) * 620, picture)
            states.append({"frame": i, "phase": m.phase, "angle": m.record_angle,
                           "arm": m.arm_angle, "lift": m.arm_lift, "opacity": m.record_opacity,
                           "requested_track": d.track.id, "display_track": d.display_track.id,
                           "is_playing": w.is_playing, "visual_playing": w.visual_playing})
            m.advance(1 / 30)
        bp.end()
        board.save(str(output / "storyboard.png"))
        (output / "frames.json").write_text(json.dumps(states, indent=2), encoding="utf-8")
    print("Saved", output, suffix or "1x + 210 frames")
    w.close()
    delete(w)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    main()
