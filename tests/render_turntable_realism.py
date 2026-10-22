"""Capture native Qt UI: --layers [--hidpi] compares against Prompt 9.1."""
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionButton
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import TRACKS
from ui.widgets import cover_art, deck_texture


def transport_states(window, output):
    """Native style rendering with explicit states, independent of cursor focus."""
    board = QPixmap(480, 390)
    board.fill(QColor("#182630"))
    p = QPainter(board)
    p.setPen(QColor("#e7caa2"))
    p.setFont(QFont("Segoe UI", 11))
    p.drawText(185, 25, "Previous")
    p.drawText(340, 25, "Next")
    states = (("Normal", QStyle.StateFlag.State_None),
              ("Hover", QStyle.StateFlag.State_MouseOver),
              ("Pressed", QStyle.StateFlag.State_Sunken),
              ("Keyboard focus", QStyle.StateFlag.State_HasFocus))
    for row, (caption, state) in enumerate(states):
        p.drawText(12, 78 + row * 86, caption)
        for column, button in enumerate((window.previous_button, window.next_button)):
            button._set_keyboard_focus(state == QStyle.StateFlag.State_HasFocus)
            option = QStyleOptionButton()
            button.initStyleOption(option)
            option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active | state
            p.save()
            p.translate(175 + column * 150, 40 + row * 86)
            p.scale(2, 2)
            button.style().drawControl(QStyle.ControlElement.CE_PushButton, option, p, button)
            p.restore()
            button._set_keyboard_focus(False)
    p.end()
    board.save(str(output / "final-static-transport-states.png"))


def render():
    hidpi = "--hidpi" in sys.argv
    polish = "--polish" in sys.argv
    approved = "--approved" in sys.argv
    final_static = "--final-static" in sys.argv
    closure = "--closure" in sys.argv or final_static
    refined = "--refined" in sys.argv or closure
    layers = "--layers" in sys.argv or approved or refined
    if hidpi:
        os.environ["QT_SCALE_FACTOR"] = "2"
    app = QApplication([])
    app.setStyle("Fusion")
    output = Path(__file__).resolve().parents[1] / "docs"
    window = MainWindow()
    if not layers:
        window.turntable._asset_art = None
    elif window.turntable.asset_error:
        raise RuntimeError(window.turntable.asset_error)
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    window.search.setText(TRACKS[0].title)
    window.top_rows[0].click()
    window.state.set_liked(TRACKS[0].id, True)
    metrics = {}
    prefix = "final-static" if final_static else "closure" if closure else "refined" if refined else "approved" if approved else ("layers" if layers else ("polish" if polish else "realism"))
    if hidpi:
        prefix += "-hidpi"
    sizes = ((1400, 900),) if hidpi and not refined else ((1120, 760), (1400, 900), (1680, 1050))
    for width, height in sizes:
        start = time.perf_counter()
        window.resize(width, height)
        app.processEvents()
        app.processEvents()
        cold_ms = (time.perf_counter() - start) * 1000
        window.grab().save(str(output / f"{prefix}-search-{width}x{height}.png"))
        deck = window.turntable
        deck.grab().save(str(output / f"{prefix}-deck-{width}x{height}.png"))
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            deck.grab()
            samples.append((time.perf_counter() - start) * 1000)
        buffers = ([*deck._asset_art.buffers.values(), deck._asset_art.label] if layers
                   else [deck._surface, *deck._layers.values()])
        metrics[f"{width}x{height}"] = {
            "screen_dpr": deck.devicePixelRatioF(),
            "resize_and_ui_ms": round(cold_ms, 2),
            "cached_deck_grab_median_ms": round(statistics.median(samples), 2),
            "cached_deck_grab_max_ms": round(max(samples), 2),
            "layer_mebibytes": round(sum(layer.width() * layer.height() * 4
                for layer in buffers) / 1024 ** 2, 2),
        }
        if width == 1400 and not hidpi:
            # Identical window size and player crop; previous capture is untouched.
            before_name = ("closure-search-1400x900.png" if final_static else "refined-search-1400x900.png" if closure else "approved-search-1400x900.png" if refined else "layers-search-1400x900.png" if approved else
                           "polish-search-1400x900.png" if layers else
                           ("realism-search-1400x900.png" if polish else "playback-search-1400x900.png"))
            before = QPixmap(str(output / before_name))
            after = window.grab()
            crop = QRect(22, 59, 874, 821)
            comparison = QPixmap(crop.width() * 2, crop.height() + 38)
            comparison.fill(QColor("#101b25"))
            painter = QPainter(comparison)
            painter.setFont(QFont("Segoe UI", 12))
            painter.setPen(QColor("#dfc69e"))
            painter.drawText(18, 25, "ANTES · PROMPT 10.3" if final_static else "ANTES · PROMPT 10.2" if closure else "ANTES · PROMPT 10.1" if refined else "ANTES · PROMPT 10" if approved else "ANTES · PROMPT 9.1" if layers else
                             ("ANTES · PROMPT 9" if polish else "ANTES · PROMPT 8"))
            painter.drawText(crop.width() + 18, 25, "DESPUÉS · PROMPT 10.4" if final_static else "DESPUÉS · PROMPT 10.3" if closure else "DESPUÉS · PROMPT 10.2" if refined else "DESPUÉS · DISEÑO APROBADO" if approved else "DESPUÉS · CAPAS GRÁFICAS" if layers else
                             ("DESPUÉS · PROMPT 9.1" if polish else "DESPUÉS · PROMPT 9"))
            painter.drawPixmap(0, 38, before.copy(crop))
            painter.drawPixmap(crop.width(), 38, after.copy(crop))
            painter.end()
            comparison.save(str(output / f"{prefix}-comparison.png"))
            if approved:
                reference = QPixmap(str(output.parent / "assets/reference/approved_turntable_concept.png"))
                deck_capture = deck.grab()
                panel_width, panel_height = 874, 710
                reference_comparison = QPixmap(panel_width * 2, panel_height + 38)
                reference_comparison.fill(QColor("#101b25"))
                p = QPainter(reference_comparison)
                p.setFont(QFont("Segoe UI", 12))
                p.setPen(QColor("#dfc69e"))
                for index, (caption, picture) in enumerate((("REFERENCIA APROBADA", reference),
                                                            ("TOCADISCOS EN LA APP", deck_capture))):
                    p.drawText(index * panel_width + 18, 25, caption)
                    scaled = picture.scaled(panel_width, panel_height, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
                    p.drawPixmap(index * panel_width + (panel_width - scaled.width()) // 2,
                                 38 + (panel_height - scaled.height()) // 2, scaled)
                p.end()
                reference_comparison.save(str(output / "approved-reference-comparison.png"))
    # An alternate label also verifies that the new art remains track-dependent.
    window.rows[1].click()
    app.processEvents()
    window.turntable.grab().save(str(output / f"{prefix}-alternate-label.png"))
    if final_static and not hidpi:
        transport_states(window, output)
    print(json.dumps(metrics, indent=2))
    if layers:
        (output / f"{prefix}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    window.close()
    delete(window)
    cover_art.cache_clear()
    deck_texture.cache_clear()
    delete(app)


if __name__ == "__main__":
    render()
