"""Mechanical record-change phases, latest-request wins and playback gating."""
import socket
import sys
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt, QTimer, QAbstractAnimation
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import TRACKS, ALBUMS, PLAYLISTS, ARTISTS
from ui.widgets import TrackRow, cover_art, deck_texture


class RecordChangeTests(unittest.TestCase):
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
        offline = patch.object(socket.socket, "connect", side_effect=AssertionError("Offline only"))
        offline.start()
        self.addCleanup(offline.stop)
        self.errors = []
        hook = sys.excepthook
        sys.excepthook = lambda *args: self.errors.append(args)
        self.addCleanup(setattr, sys, "excepthook", hook)
        self.w = MainWindow()
        self.w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.w.show()
        self.app.processEvents()
        self.deck, self.m = self.w.turntable, self.w.turntable.motion
        self.m.set_active(False)
        self.m.advance(1.2)
        self.deck.grab()

    def tearDown(self):
        self.w.close()
        delete(self.w)
        self.assertEqual(self.errors, [])

    def test_phases_lift_withdraw_empty_swap_land_then_rotate(self):
        m, w, deck = self.m, self.w, self.deck
        pose, angle = m.arm_angle, m.record_angle
        signals = QSignalSpy(m.transition_changed)
        swaps = QSignalSpy(m.record_swapped)
        w.next_button.click()
        self.assertEqual(m.phase, "lift")
        self.assertEqual(m.arm_angle, pose)
        self.assertIs(deck.display_track, TRACKS[0])
        self.assertIs(deck.track, TRACKS[1])
        self.assertTrue(w.is_playing)
        self.assertFalse(w.visual_playing)
        self.assertEqual(w.status.text(), "CHANGING RECORD")
        m.advance(.22)
        self.assertEqual(m.phase, "withdraw")
        self.assertEqual(m.arm_lift, 1)
        self.assertEqual(m.arm_angle, pose)
        m.advance(.42)
        self.assertEqual(m.phase, "remove")
        self.assertEqual(m.arm_angle, m.rest_angle)
        m.advance(.32)
        self.assertEqual(m.phase, "empty")
        self.assertEqual(m.record_opacity, 0)
        self.assertIs(deck.display_track, TRACKS[0])
        m.advance(.10)
        self.assertEqual(swaps.count(), 1)
        self.assertEqual(m.phase, "insert")
        self.assertIs(deck.display_track, TRACKS[1])
        self.assertEqual(m.record_angle, 0)
        m.advance(.32 + .42)
        self.assertEqual(m.phase, "lower")
        self.assertEqual(m.arm_lift, 1)
        self.assertAlmostEqual(m.arm_angle, m.outer_angle)
        self.assertEqual(m.record_angle, 0)
        m.advance(.22)
        self.assertFalse(m.changing)
        self.assertTrue(w.visual_playing)
        self.assertEqual(m.arm_lift, 0)
        self.assertEqual(m.record_opacity, 1)
        self.assertEqual(signals.count(), 2)
        m.advance(.1)
        self.assertAlmostEqual(m.record_angle, 20)
        self.assertNotEqual(angle, m.record_angle)

    def test_pause_and_resume_at_every_phase_keep_latest_play_intent(self):
        for phase_index in range(len(self.m.PHASES)):
            for playing in (False, True):
                with self.subTest(phase=phase_index, playing=playing):
                    self.w._show_track(TRACKS[(self.w.current_index + 1) % len(TRACKS)])
                    self.m.advance(sum(d for _, d in self.m.PHASES[:phase_index]) + .01)
                    if self.w.is_playing != playing:
                        self.w.play_button.click()
                    self.m.advance(3)
                    self.assertFalse(self.m.changing)
                    self.assertEqual(self.m.rotating, playing)
                    self.assertEqual(self.w.visual_playing, playing)
                    angle = self.m.record_angle
                    self.m.advance(.1)
                    self.assertAlmostEqual(self.m.record_angle, (angle + (20 if playing else 0)) % 360)
                    self.assertEqual(self.m.arm_lift, 0)
                    self.assertIs(self.deck.display_track, self.w.current_track)

    def test_rapid_requests_at_every_phase_preserve_pose_and_finish_latest(self):
        timers = self.deck.findChildren(QTimer)
        animations = self.deck.findChildren(QAbstractAnimation)
        for phase_index in range(len(self.m.PHASES)):
            self.w._show_track(TRACKS[1])
            self.m.advance(sum(d for _, d in self.m.PHASES[:phase_index]) + .05)
            for track in (TRACKS[2], TRACKS[4], TRACKS[0], TRACKS[3]):
                pose = self.m.arm_angle, self.m.arm_lift, self.m.record_opacity
                self.w._show_track(track)
                self.assertEqual((self.m.arm_angle, self.m.arm_lift, self.m.record_opacity), pose)
            self.m.advance(4)
            self.assertFalse(self.m.changing)
            self.assertIs(self.deck.display_track, TRACKS[3])
            self.assertEqual(self.m.record_opacity, 1)
            self.assertAlmostEqual(self.m.arm_angle, self.m.outer_angle)
        self.assertEqual(timers, self.deck.findChildren(QTimer))
        self.assertEqual(animations, self.deck.findChildren(QAbstractAnimation))

    def test_all_routes_and_equalizers_wait_for_landing(self):
        w = self.w
        w.playlists.open_playlist(PLAYLISTS[0])
        w.albums.open_album(ALBUMS[0].id)
        w.artist_profile.open_artist(ARTISTS[0].id)
        w.state.set_liked(TRACKS[1].id, True)
        w.state.add_to_queue(TRACKS[2].id)
        rows = [w.rows[1], w.top_rows[0], w.playlists.track_rows[1], w.albums.track_rows[1],
                w.liked.rows[0], w.artist_profile.track_rows[1], w.queue_rows[0]]
        for row in rows:
            w._show_track(TRACKS[5] if row.track != TRACKS[5] else TRACKS[0])
            self.m.advance(3)
            row.click()
            self.assertTrue(self.m.changing)
            self.assertFalse(w.visual_playing)
            self.assertIs(self.deck.track, row.track)
            for item in w.findChildren(TrackRow):
                self.assertNotEqual(item.indicator.animation.state(), QAbstractAnimation.State.Running)
            self.m.advance(3)
            self.assertIs(self.deck.display_track, row.track)
            self.assertTrue(w.visual_playing)
            for item in w.findChildren(TrackRow):
                running = item.indicator.animation.state() == QAbstractAnimation.State.Running
                self.assertEqual(running, item.isVisible() and item.track.id == row.track.id)
        w.previous_button.click()
        self.assertTrue(self.m.changing)

    def test_real_timer_completes_paused_exchange_without_fake_play_events(self):
        self.w.play_button.click()
        playback = QSignalSpy(self.w.playback_toggled)
        selection = QSignalSpy(self.w.track_selected)
        self.w.next_button.click()
        completed = QSignalSpy(self.m.transition_changed)
        self.m.set_active(True, self.deck.devicePixelRatioF())
        self.assertTrue(self.m.timer.isActive())
        self.assertTrue(completed.wait(3500))
        self.assertEqual(completed.at(0), [False])
        self.assertEqual(playback.count(), 0)
        self.assertEqual(selection.count(), 1)
        self.assertFalse(self.m.timer.isActive())
        self.assertFalse(self.w.is_playing)
        self.assertIs(self.deck.display_track, self.w.current_track)

    def test_same_track_does_not_exchange_and_slider_retargets_afterward(self):
        self.w._show_track(TRACKS[0])
        self.assertFalse(self.m.changing)
        self.w.next_button.click()
        self.m.advance(1.7)
        self.w.progress.setValue(self.w.progress.maximum())
        self.m.advance(2)
        self.assertAlmostEqual(self.m.arm_angle, self.m.inner_angle)
        self.w.progress.setValue(0)
        self.m.advance(.5)
        self.assertAlmostEqual(self.m.arm_angle, self.m.outer_angle)

    def test_empty_platter_and_delayed_cover_with_cached_fade(self):
        art = self.deck._asset_art
        label = art.label.toImage()
        base_keys = {name: p.cacheKey() for name, p in art.buffers.items()}
        with patch("ui.turntable_assets.QImageReader", side_effect=AssertionError("Frame I/O")):
            self.w.next_button.click()
            self.deck.grab()
            self.assertEqual(label, art.label.toImage())
            self.m.advance(.85)
            self.deck.grab()
            fade_key = art.disc_frame.cacheKey()
            self.m.advance(.05)
            self.deck.grab()
            self.assertEqual(fade_key, art.disc_frame.cacheKey())
            self.m.advance(.1)
            empty = self.deck.grab().toImage()
            self.assertEqual(self.m.record_opacity, 0)
            self.m.advance(.25)
            inserted = self.deck.grab().toImage()
            self.assertNotEqual(label, art.label.toImage())
            self.assertNotEqual(empty, inserted)
            self.assertEqual(base_keys, {name: p.cacheKey() for name, p in art.buffers.items()})

    def test_resize_and_hide_mid_exchange_keep_pending_destination(self):
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            self.w.next_button.click()
            self.m.advance(.8)
            self.w.resize(*size)
            self.app.processEvents()
            self.deck.grab()
            self.assertTrue(self.deck.rect().contains(self.deck._transport.geometry()))
            self.w.hide()
            self.assertFalse(self.m.timer.isActive())
            phase = self.m.phase
            self.w.show()
            self.m.set_active(False)
            self.assertEqual(self.m.phase, phase)
            self.m.advance(3)
            self.assertIs(self.deck.display_track, self.w.current_track)


if __name__ == "__main__":
    unittest.main()
