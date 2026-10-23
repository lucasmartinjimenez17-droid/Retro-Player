"""Offline native-Qt screenshots and reproducible 30 fps animation frames.

Run with the app venv, optionally --hidpi. Source artwork is never modified.
"""
import json
import os
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if "--hidpi" in sys.argv:
    os.environ["QT_SCALE_FACTOR"] = "2"

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from shiboken6 import delete
from main_window import MainWindow
from ui.widgets import Turntable, cover_art, deck_texture


def main():
    paint_samples = []
    original_paint = Turntable.paintEvent
    def measured_paint(self, event):
        start = time.perf_counter()
        original_paint(self, event)
        paint_samples.append((time.perf_counter() - start) * 1000)
    Turntable.paintEvent = measured_paint
    app = QApplication([])
    app.setStyle("Fusion")
    w = MainWindow()
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    w.show()
    app.processEvents()
    deck, output = w.turntable, Path(__file__).resolve().parents[1] / "docs" / "motion"
    output.mkdir(exist_ok=True)
    m = deck.motion
    m.set_active(False)
    m.advance(1.2)
    suffix = "-2x" if "--hidpi" in sys.argv else ""
    metrics = {}
    for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
        w.resize(width, height)
        app.processEvents()
        w.grab().save(str(output / f"app-{width}x{height}{suffix}.png"))
        samples = []
        paint_samples.clear()
        for _ in range(40):
            m.advance(1 / 60)
            start = time.perf_counter()
            deck.grab()
            samples.append((time.perf_counter() - start) * 1000)
        art = deck._asset_art
        buffers = [*art.buffers.values(), *art.record_parts, art.label, art.arm_overlay, deck._static_scene]
        metrics[f"{width}x{height}"] = {
            "dpr": deck.devicePixelRatioF(),
            "frame_grab_median_ms": round(statistics.median(samples), 2),
            "frame_grab_p95_ms": round(sorted(samples)[37], 2),
            "paint_median_ms": round(statistics.median(paint_samples), 2),
            "paint_p95_ms": round(sorted(paint_samples)[int(len(paint_samples) * .95) - 1], 2),
            "widget_cache_mib": round(sum(p.width() * p.height() * 4 for p in buffers) / 1024 ** 2, 2),
        }
    (output / f"metrics{suffix}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    if not suffix:
        # Fresh initial state, but paused before first paint so entry starts at
        # the actual mechanical rest position. Each frame advances exactly 1/30 s.
        delete(w)
        w = MainWindow()
        w._toggle_playback()
        w.resize(1120, 760)
        w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        w.show()
        app.processEvents()
        deck, m = w.turntable, w.turntable.motion
        m.set_active(False)
        w.progress.setValue(0)
        frames = output / "frames"
        frames.mkdir(exist_ok=True)
        sheet = QPixmap(1280, 3 * 620)
        sheet.fill(QColor("#101b25"))
        sheet_p = QPainter(sheet)
        sample_frames = (0, 30, 75, 120, 165, 225)
        captions = []
        for i in range(240):
            if i == 15:
                w._toggle_playback()
            elif i == 90:
                w._toggle_playback()
            elif i == 135:
                w._toggle_playback()
            elif i == 165:
                w.progress.setValue(w.progress.maximum())
            elif i == 210:
                w.next_button.click()
            caption = ("REPOSO" if i < 15 else "ENTRADA / PLAY" if i < 90 else
                       "PAUSA" if i < 135 else "REANUDAR" if i < 165 else
                       "SLIDER AL FINAL" if i < 210 else "NEXT / NUEVA PORTADA")
            picture = QPixmap(640, 620)
            picture.fill(QColor("#101b25"))
            p = QPainter(picture)
            p.setPen(QColor("#e7c99d"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(12, 24, f"{i / 30:.2f} s · {caption} · {m.record_angle:.1f}°")
            shot = deck.grab().scaled(640, 580, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((640 - shot.width()) // 2, 38, shot)
            p.end()
            picture.save(str(frames / f"{i:03d}.webp"), "WEBP", 92)
            if i in sample_frames:
                n = sample_frames.index(i)
                sheet_p.drawPixmap((n % 2) * 640, (n // 2) * 620, picture)
            captions.append({"frame": i, "time": i / 30, "state": caption,
                             "record_angle": m.record_angle, "arm_angle": m.arm_angle,
                             "slider_seconds": w.progress.value(), "track": w.current_track.id})
            m.advance(1 / 30)
        sheet_p.end()
        sheet.save(str(output / "storyboard.png"))
        (output / "frames.json").write_text(json.dumps(captions, indent=2), encoding="utf-8")
    w.close()
    delete(w)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)
    Turntable.paintEvent = original_paint


if __name__ == "__main__":
    main()
