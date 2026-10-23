"""Offline motion, geometry, lifecycle and rendering regressions."""
import math
import socket
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap, QTransform
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete, isValid

from main_window import MainWindow
from ui.mock_data import ALBUMS, ARTISTS, PLAYLISTS, TRACKS
from ui.turntable_assets import load_artwork, LayeredTurntable
from ui.turntable_motion import TurntableMotion
from ui.widgets import cover_art, deck_texture


class TurntableMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owns_app = QApplication.instance() is None
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    @classmethod
    def tearDownClass(cls):
        cover_art.cache_clear()
        deck_texture.cache_clear()
        if cls.owns_app:
            delete(cls.app)

    def setUp(self):
        network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden"))
        network.start()
        self.addCleanup(network.stop)
        self.pack = load_artwork()[0]
        self.motion = TurntableMotion(self.pack.metadata)
        self.addCleanup(delete, self.motion)

    def window(self):
        w = MainWindow()
        w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        w.show()
        self.app.processEvents()
        w.turntable.motion.set_active(False)
        self.addCleanup(delete, w)
        return w

    def test_clockwise_exact_rpm_wrap_and_frame_rate_independence(self):
        m = self.motion
        m.set_playing(True)
        m.advance(.45)
        self.assertAlmostEqual(m.record_angle, 90)
        m.advance(1.35)
        self.assertAlmostEqual(m.record_angle, 0)
        for _ in range(54):
            m.advance(1 / 30)
        self.assertAlmostEqual(m.record_angle % 360, 0, places=8)
        m.advance(12.34)
        self.assertAlmostEqual(m.record_angle, (12.34 * 200) % 360, places=8)

    def test_pause_resume_preserve_pose_and_do_not_recue(self):
        m = self.motion
        m.set_playing(True)
        m.advance(1.2)
        pose = m.record_angle, m.arm_angle
        m.set_playing(False)
        m.advance(9)
        self.assertEqual((m.record_angle, m.arm_angle), pose)
        self.assertNotEqual(m.arm_angle, m.rest_angle)
        m.set_playing(True)
        self.assertFalse(m.arm_moving)
        m.advance(.1)
        self.assertAlmostEqual(m.record_angle, (pose[0] + 20) % 360)
        self.assertEqual(m.arm_angle, pose[1])

    def test_entry_and_rapid_seek_retarget_without_jump_or_overshoot(self):
        m = self.motion
        m.set_playing(True)
        previous = m.arm_angle
        for _ in range(21):
            m.advance(.05)
            self.assertGreaterEqual(m.arm_angle, previous)
            self.assertLessEqual(m.arm_angle, m.outer_angle)
            previous = m.arm_angle
        self.assertAlmostEqual(m.arm_angle, m.outer_angle)
        for progress in (100, 10, 75, 0, 90, 100):
            pose = m.arm_angle
            m.set_progress(progress, 100)
            self.assertEqual(m.arm_angle, pose)
            m.advance(.08)
            self.assertGreaterEqual(m.arm_angle, m.outer_angle)
            self.assertLessEqual(m.arm_angle, m.inner_angle)
        m.advance(.5)
        self.assertAlmostEqual(m.arm_angle, m.inner_angle)
        self.assertEqual(m.findChildren(QTimer), [m.timer])

    def test_pause_during_entry_resumes_same_transition(self):
        m = self.motion
        m.set_playing(True)
        m.advance(.2)
        pose = m.arm_angle
        m.set_playing(False)
        m.advance(3)
        self.assertEqual(m.arm_angle, pose)
        m.set_playing(True)
        self.assertEqual(m.arm_angle, pose)
        m.advance(.85)
        self.assertAlmostEqual(m.arm_angle, m.outer_angle)

    def test_seek_while_paused_moves_arm_without_turning_record(self):
        m = self.motion
        m.set_playing(True)
        m.advance(1.2)
        m.set_playing(False)
        angle = m.record_angle
        m.set_progress(50, 100)
        m.advance(.5)
        self.assertEqual(m.record_angle, angle)
        self.assertAlmostEqual(m.arm_angle, (m.inner_angle + m.outer_angle) / 2)

    def test_geometry_keeps_pivot_and_stylus_connected(self):
        m = self.motion
        pivot = QPointF(*self.pack.metadata["arm_pivot"])
        center = QPointF(*self.pack.metadata["record_center"])
        stylus = QPointF(*self.pack.metadata["stylus"])
        length = math.hypot(stylus.x() - pivot.x(), stylus.y() - pivot.y())
        for angle, ratio in ((m.rest_angle, 1.18), (m.outer_angle, .88), (m.inner_angle, .56)):
            transform = QTransform().translate(pivot.x(), pivot.y()).rotate(angle).translate(-pivot.x(), -pivot.y())
            self.assertEqual(transform.map(pivot), pivot)
            needle = transform.map(stylus)
            self.assertAlmostEqual(math.hypot(needle.x() - pivot.x(), needle.y() - pivot.y()), length)
            self.assertAlmostEqual(math.hypot(needle.x() - center.x(), needle.y() - center.y()),
                                   self.pack.metadata["record_radius"] * ratio)

    def test_real_timer_hide_resume_and_destruction(self):
        w = self.window()
        m = w.turntable.motion
        m.set_active(True)
        angle = m.record_angle
        QTest.qWait(90)
        self.assertNotEqual(m.record_angle, angle)
        w.hide()
        self.assertFalse(m.timer.isActive())
        angle = m.record_angle
        QTest.qWait(50)
        self.assertEqual(m.record_angle, angle)
        w.show()
        self.assertTrue(m.timer.isActive())
        w.setWindowState(Qt.WindowState.WindowMinimized)
        self.app.processEvents()
        self.assertFalse(m.timer.isActive())
        w.setWindowState(Qt.WindowState.WindowNoState)
        self.app.processEvents()
        self.assertTrue(m.timer.isActive())
        w._toggle_playback()
        self.assertFalse(m.timer.isActive())
        # QObject parenting deletes the single timer along with the controller.
        other = TurntableMotion(self.pack.metadata)
        timer = other.timer
        delete(other)
        self.assertFalse(isValid(timer))

    def test_startup_slider_and_selection_routes_share_mock_state(self):
        w = self.window()
        m = w.turntable.motion
        self.assertEqual(m.playing, w.is_playing)
        self.assertAlmostEqual(m.progress, w.progress.value() / w.progress.maximum())
        m.advance(20)
        self.assertEqual(w.progress.value(), 102, "Animation must not invent elapsed playback")
        w.progress.setValue(w.progress.maximum())
        m.advance(.5)
        self.assertAlmostEqual(m.arm_angle, m.inner_angle)
        w._toggle_playback()
        w.playlists.open_playlist(PLAYLISTS[0])
        w.albums.open_album(ALBUMS[0].id)
        w.artist_profile.open_artist(ARTISTS[0].id)
        w.state.set_liked(TRACKS[1].id, True)
        w.state.add_to_queue(TRACKS[2].id)
        routes = [w.rows[1], w.top_rows[0], w.playlists.track_rows[1],
                  w.albums.track_rows[1], w.liked.rows[0],
                  w.artist_profile.track_rows[1], w.queue_rows[0]]
        for row in routes:
            row.click()
            self.assertIs(w.current_track, row.track)
            self.assertIs(w.turntable.track, row.track)
            self.assertFalse(m.playing)
            self.assertEqual(m.progress, 0)
        for _ in range(30):
            w.next_button.click()
            w.previous_button.click()
        self.assertEqual(w.turntable.findChildren(QTimer), [m.timer])
        self.assertFalse(w.is_playing)

    def test_render_rotates_label_with_surface_keeps_center_and_static_pixels(self):
        art = LayeredTurntable(self.pack)
        art.prepare(1, 1, cover_art(TRACKS[0].colors, 512, circular=True))
        def frame(angle):
            pix = QPixmap(820, 650)
            pix.fill(QColor("#101b25"))
            p = QPainter(pix)
            p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
            art.paint(p, angle, self.motion.outer_angle)
            p.end()
            return pix.toImage()
        first, quarter, full = frame(0), frame(90), frame(360)
        self.assertEqual(first, full)
        self.assertEqual(art.record_clip().boundingRect().center(), QPointF(399, 291))
        # Label sample follows the same clockwise transformation as the surface.
        self.assertEqual(first.pixelColor(399, 231), quarter.pixelColor(459, 291))
        self.assertNotEqual(first.copy(310, 202, 178, 178), quarter.copy(310, 202, 178, 178))
        for rect in ((5, 20, 110, 600), (398, 290, 2, 2), (650, 80, 140, 80)):
            self.assertEqual(first.copy(*rect), quarter.copy(*rect))

    def test_frames_and_track_changes_reuse_decoded_layers_and_static_scene(self):
        w = self.window()
        deck = w.turntable
        deck.grab()
        art = deck._asset_art
        deck.motion.advance(2)
        deck.grab()
        arm_key = art.arm_overlay.cacheKey()
        static_key = deck._static_scene.cacheKey()
        layers = [p.cacheKey() for p in (*art.buffers.values(), *art.record_parts)]
        old_label = art.label.cacheKey()
        with patch("ui.turntable_assets.QImageReader", side_effect=AssertionError("Frame file I/O")):
            for _ in range(12):
                deck.motion.advance(.07)
                deck.grab()
            self.assertEqual(arm_key, art.arm_overlay.cacheKey())
            w.next_button.click()
            self.assertEqual(art.label.cacheKey(), old_label)
            deck.motion.advance(3)
            deck.grab()
        self.assertEqual(deck._static_scene.cacheKey(), static_key)
        self.assertEqual([p.cacheKey() for p in (*art.buffers.values(), *art.record_parts)], layers)
        self.assertNotEqual(art.label.cacheKey(), old_label)
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            self.app.processEvents()
            deck.grab()
            self.assertEqual(len(art.record_parts), 2)
            self.assertTrue(deck.rect().contains(deck._transport.geometry()))


if __name__ == "__main__":
    unittest.main()
