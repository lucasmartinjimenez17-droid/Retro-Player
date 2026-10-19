"""Offline UI checks. Run: python -m unittest discover -s tests -v."""
import socket
import sys
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QFrame
from shiboken6 import delete

from main_window import MainWindow
from ui.mock_data import ALBUMS, ALBUMS_BY_ID, PLAYLISTS, TRACKS, INITIAL_SAVED_ALBUM_IDS, TRACKS_BY_ID
from ui.widgets import cover_art, deck_texture


class FrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owns_app = QApplication.instance() is None
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    @classmethod
    def tearDownClass(cls):
        # Dispose native Qt objects before Python interpreter finalization.
        cover_art.cache_clear()
        deck_texture.cache_clear()
        if cls.owns_app:
            delete(cls.app)

    def setUp(self):
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.exceptions = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda *args: self.exceptions.append(args)
        self.addCleanup(setattr, sys, "excepthook", self.old_hook)
        self.window = MainWindow()
        # Native Windows fonts, without window-manager size restrictions.
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.assertFalse(self.window.isVisible())
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual(self.exceptions, [], "Exception in a Qt callback")

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def tab(self, text):
        self.click(next(b for b in self.window.tabs.buttons() if b.text() == text))

    def test_startup_is_offline(self):
        self.assertNotIn("auth", sys.modules)
        self.assertNotIn("spotify_api", sys.modules)
        self.assertEqual(self.window.song_title.text(), TRACKS[0].title)
        self.assertEqual(self.window.elapsed.text(), "1:42")
        self.assertTrue(self.window.rows[0].isChecked())

    def test_transport_and_selection_stay_in_sync(self):
        w = self.window
        playback = QSignalSpy(w.playback_toggled)
        selection = QSignalSpy(w.track_selected)
        self.click(w.play_button)
        self.assertFalse(w.is_playing)
        self.assertEqual(playback.at(0), [False])
        self.click(w.next_button)
        self.assertEqual(w.song_title.text(), TRACKS[1].title)
        self.assertEqual(w.turntable.track, TRACKS[1])
        self.assertEqual(w.progress.value(), 0)
        self.click(w.previous_button)
        self.click(w.previous_button)
        self.assertEqual(w.current_index, len(TRACKS) - 1)
        self.click(w.rows[0])
        self.assertEqual(w.current_index, 0)
        self.assertEqual(sum(row.isChecked() for row in w.rows), 1)
        self.assertEqual(selection.count(), 4)

    def test_search_empty_state_and_navigation(self):
        w = self.window
        w.search.setText("velvet")
        self.assertEqual(sum(not row.isHidden() for row in w.rows), 2)
        w.search.setText("no-such-record")
        self.assertTrue(w.empty.isVisible())
        w.search.clear()
        self.assertFalse(w.empty.isVisible())
        self.tab("Albums")
        self.assertIs(w.albums.currentWidget(), w.albums.library_page)
        self.tab("Playlists")
        self.assertIs(w.playlists.currentWidget(), w.playlists.library_page)
        self.tab("Queue")
        self.assertEqual(w.result_count.text(), "5 tracks")
        self.assertTrue(w.rows[w.current_index].isHidden())
        start = w.rows_layout.indexOf(w.heading_widget) + 1
        self.assertEqual(w.rows_layout.itemAt(start).widget().index, 1)
        self.click(w.next_button)
        self.assertEqual(w.rows_layout.itemAt(start).widget().index, 2)
        self.tab("Search")
        self.assertEqual(w.result_count.text(), "6 tracks")
        self.assertEqual(w.rows_layout.itemAt(start).widget().index, 0)

    def test_sliders_and_keyboard(self):
        w = self.window
        seek = QSignalSpy(w.seek_requested)
        volume = QSignalSpy(w.volume_changed)
        w.progress.setValue(120)
        self.assertEqual(w.elapsed.text(), "2:00")
        self.assertEqual(seek.at(0), [120])
        w.volume.setValue(0)
        self.assertEqual(w.volume_value.text(), "0%")
        w.volume.setFocus()
        QTest.keyClick(w.volume, Qt.Key.Key_Right)
        self.assertEqual(w.volume.value(), 1)
        self.assertEqual(volume.count(), 2)
        w.play_button.setFocus()
        QTest.keyClick(w.play_button, Qt.Key.Key_Space)
        self.assertFalse(w.is_playing)

    def test_layout_and_paint_at_supported_sizes(self):
        w = self.window
        for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
            with self.subTest(size=(width, height)):
                w.resize(width, height)
                self.app.processEvents()
                self.assertEqual(w.size().toTuple(), (width, height))
                self.assertFalse(w.grab().isNull())
                panel = w.findChild(QFrame, "sidebar")
                self.assertLessEqual(panel.geometry().right(), w.width())
                graphic_bottom = w.turntable.mapTo(w, w.turntable.rect().bottomRight()).y()
                song_top = w.sleeve.mapTo(w, w.sleeve.rect().topLeft()).y()
                self.assertLess(graphic_bottom, song_top)
                self.assertTrue(w.play_button.isVisible())

    def test_playlist_library_and_back_navigation(self):
        w = self.window
        browser = w.playlists
        w.search.setText("no-such-record")
        self.tab("Playlists")
        self.assertIs(w.sidebar_pages.currentWidget(), browser)
        self.assertFalse(w.search.isVisible())
        self.assertEqual([row.playlist for row in browser.library_rows], list(PLAYLISTS))
        self.assertEqual(len({p.id for p in PLAYLISTS}), 5)
        self.assertEqual(len({len(p.track_indices) for p in PLAYLISTS}), 5)
        self.click(browser.library_rows[1])
        self.assertIs(browser.currentWidget(), browser.detail_page)
        self.assertEqual(browser.playlist_title.text(), PLAYLISTS[1].name)
        self.click(browser.back_button)
        self.assertIs(browser.currentWidget(), browser.library_page)
        self.assertTrue(browser.library_rows[1].isChecked())
        self.assertIs(browser.focusWidget(), browser.library_rows[1])
        self.tab("Search")
        self.assertEqual(w.search.text(), "no-such-record")
        self.assertTrue(w.empty.isVisible())

    def test_playlist_contents_selection_and_signals(self):
        w = self.window
        browser = w.playlists
        selected = QSignalSpy(w.track_selected)
        toggled = QSignalSpy(w.playback_toggled)
        self.tab("Playlists")
        for playlist, library_row in zip(PLAYLISTS, browser.library_rows):
            self.click(library_row)
            rows = [row for row in browser.track_rows if not row.isHidden()]
            self.assertEqual(tuple(row.index for row in rows), playlist.track_indices)
            self.assertEqual([row.track for row in rows], [TRACKS[i] for i in playlist.track_indices])
            self.assertEqual(browser.playlist_count.text(), f"{len(rows)} songs")
            self.click(rows[-1])
            expected = TRACKS[playlist.track_indices[-1]]
            self.assertEqual(w.song_title.text(), expected.title)
            self.assertEqual(w.turntable.track, expected)
            self.assertEqual(selected.at(selected.count() - 1), [expected])
            self.assertEqual(sum(row.isChecked() for row in rows), 1)
            self.click(browser.back_button)
        self.assertEqual(selected.count(), len(PLAYLISTS))
        self.assertEqual(toggled.count(), 0)

    def test_playlist_play_resumes_and_keeps_transport_compatible(self):
        w = self.window
        self.click(w.play_button)
        self.tab("Playlists")
        self.click(w.playlists.library_rows[2])
        self.click(w.playlists.track_rows[1])
        self.assertFalse(w.is_playing)  # Selecting a row must not change pause state.
        selected = QSignalSpy(w.track_selected)
        toggled = QSignalSpy(w.playback_toggled)
        seek = QSignalSpy(w.seek_requested)
        self.click(w.playlists.play_button)
        first = PLAYLISTS[2].track_indices[0]
        self.assertEqual(w.current_index, first)
        self.assertTrue(w.is_playing)
        self.assertEqual(w.progress.value(), 0)
        self.assertEqual(selected.at(0), [TRACKS[first]])
        self.assertEqual(toggled.at(0), [True])
        self.assertEqual(seek.count(), 0)
        self.click(w.playlists.play_button)
        self.assertEqual(toggled.count(), 1)  # No spurious toggle when already playing.
        self.assertEqual(selected.count(), 2)
        self.click(w.next_button)
        self.assertEqual(w.current_index, (first + 1) % len(TRACKS))
        self.click(w.previous_button)
        self.assertEqual(w.current_index, first)
        self.assertTrue(w.playlists.track_rows[0].isChecked())

    def test_repeated_playlist_and_tab_navigation_reuses_widgets(self):
        w = self.window
        browser = w.playlists
        row_ids = [id(row) for row in browser.track_rows]
        for _ in range(3):
            for row in browser.library_rows:
                self.tab("Playlists")
                self.assertIs(browser.currentWidget(), browser.library_page)
                self.click(row)
                self.click(browser.track_rows[0])
                # Clicking the current tab is also a predictable return to the library.
                self.tab("Playlists")
                self.assertIs(browser.currentWidget(), browser.library_page)
                for name in ("Albums", "Queue", "Search"):
                    self.tab(name)
                    expected = w.albums if name == "Albums" else w.catalog_page
                    self.assertIs(w.sidebar_pages.currentWidget(), expected)
        self.assertEqual(row_ids, [id(row) for row in browser.track_rows])
        self.assertEqual(browser.count(), 2)
        self.assertEqual(w.sidebar_pages.count(), 5)

    def test_playlist_layout_scroll_and_keyboard_at_supported_sizes(self):
        from dataclasses import replace

        w = self.window
        browser = w.playlists
        for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
            with self.subTest(size=(width, height)):
                w.resize(width, height)
                self.tab("Playlists")
                self.assertFalse(w.grab().isNull())
                background = browser.library_scroll.viewport().grab().toImage().pixelColor(0, 0)
                self.assertLess(max(background.red(), background.green(), background.blue()), 100)
                browser.library_rows[0].setFocus()
                QTest.keyClick(browser.library_rows[0], Qt.Key.Key_Space)
                self.app.processEvents()
                self.assertIs(browser.currentWidget(), browser.detail_page)
                row = browser.track_rows[0]
                row.track = replace(row.track, title="A very long song title " * 8)
                self.assertFalse(w.grab().isNull())
                self.assertLessEqual(row.width(), browser.detail_scroll.viewport().width())
                self.assertTrue(browser.play_button.isVisible())
                self.assertTrue(browser.back_button.isVisible())
                self.assertEqual(browser.detail_scroll.horizontalScrollBar().maximum(), 0)
                background = browser.detail_scroll.viewport().grab().toImage().pixelColor(0, 0)
                self.assertLess(max(background.red(), background.green(), background.blue()), 100)
                if height == 760:
                    self.assertGreater(browser.detail_scroll.verticalScrollBar().maximum(), 0)
                browser.detail_scroll.ensureWidgetVisible(browser.track_rows[-1])
                self.app.processEvents()
                self.click(browser.track_rows[-1])
                self.assertEqual(w.current_index, PLAYLISTS[0].track_indices[-1])
                self.click(browser.back_button)
                self.assertIs(browser.currentWidget(), browser.library_page)


    def test_album_cards_only_navigate_and_back_preserves_library(self):
        w, browser = self.window, self.window.albums
        selected = QSignalSpy(w.track_selected)
        toggled = QSignalSpy(w.playback_toggled)
        w.search.setText("velvet")
        self.tab("Albums")
        self.assertIs(w.sidebar_pages.currentWidget(), browser)
        self.assertEqual([card.album.id for card in browser.cards], list(INITIAL_SAVED_ALBUM_IDS))
        for card in browser.cards:
            browser.library_scroll.ensureWidgetVisible(card)
            self.app.processEvents()
            scroll_position = browser.library_scroll.verticalScrollBar().value()
            self.click(card)
            self.assertIs(browser.currentWidget(), browser.detail_page)
            self.assertEqual(browser.selected_album_id, card.album.id)
            self.assertEqual(browser.header.title.text(), card.album.name)
            self.assertEqual(browser.header.artist.text(), card.album.artist)
            self.assertIn(str(card.album.year), browser.header.metadata.text())
            self.assertEqual(w.current_track, TRACKS[0])
            self.assertEqual(w.progress.value(), 102)
            self.click(browser.back_button)
            self.assertIs(browser.currentWidget(), browser.library_page)
            self.assertTrue(card.isChecked())
            self.assertIs(browser.focusWidget(), card)
            self.assertEqual(browser.library_scroll.verticalScrollBar().value(), scroll_position)
        self.assertEqual(selected.count(), 0)
        self.assertEqual(toggled.count(), 0)
        self.tab("Search")
        self.assertEqual(w.search.text(), "velvet")
        self.assertEqual(w.result_count.text(), "2 tracks")

    def test_album_membership_order_numbering_and_track_selection(self):
        w, browser = self.window, self.window.albums
        selected = QSignalSpy(w.track_selected)
        self.tab("Albums")
        self.assertEqual(len(ALBUMS_BY_ID), len(ALBUMS))
        for album in ALBUMS:
            browser.open_album(album.id)
            self.app.processEvents()
            rows = [row for row in browser.track_rows if not row.isHidden()]
            self.assertEqual(tuple(row.track for row in rows), album.tracks)
            self.assertEqual([row.track_number for row in rows], list(range(1, len(rows) + 1)))
            self.assertTrue(all(row.track.album_id == album.id for row in rows))
            self.assertTrue(all(row.track.album == album.name for row in rows))
            self.assertTrue(all(row.track.colors == album.colors for row in rows))
            browser.detail_scroll.ensureWidgetVisible(rows[-1])
            self.click(rows[-1])
            self.assertEqual(w.current_track, album.tracks[-1])
            self.assertEqual(w.song_title.text(), album.tracks[-1].title)
            self.assertEqual(w.turntable.track, album.tracks[-1])
            self.assertEqual(w.progress.maximum(), album.tracks[-1].seconds)
            self.assertEqual(w.progress.value(), 0)
            self.assertEqual(sum(row.isChecked() for row in rows), 1)
            self.assertEqual(selected.at(selected.count() - 1), [album.tracks[-1]])
        self.assertEqual(selected.count(), len(ALBUMS))

    def test_play_album_and_shared_selection_preserve_signal_meaning(self):
        w, browser = self.window, self.window.albums
        self.click(w.play_button)
        self.tab("Albums")
        self.click(browser.cards[0])
        self.click(browser.track_rows[2])
        self.assertFalse(w.is_playing)
        self.assertIsNone(w.current_index)
        selected = QSignalSpy(w.track_selected)
        toggled = QSignalSpy(w.playback_toggled)
        seek = QSignalSpy(w.seek_requested)
        self.click(browser.header.play_button)
        self.assertEqual(w.current_track, ALBUMS[0].tracks[0])
        self.assertTrue(w.is_playing)
        self.assertEqual(selected.at(0), [ALBUMS[0].tracks[0]])
        self.assertEqual(toggled.at(0), [True])
        self.assertEqual(seek.count(), 0)
        self.click(browser.header.play_button)
        self.assertEqual(toggled.count(), 1)
        self.assertEqual(selected.count(), 2)
        self.tab("Playlists")
        self.click(w.playlists.library_rows[0])
        self.assertTrue(w.playlists.track_rows[0].isChecked())
        self.click(w.playlists.track_rows[1])
        self.tab("Albums")
        browser.open_album(TRACKS[4].album_id)
        self.assertTrue(browser.track_rows[0].isChecked())

    def test_album_exclusive_track_does_not_change_other_catalogues(self):
        w, browser = self.window, self.window.albums
        self.tab("Albums")
        self.click(browser.cards[0])
        self.click(browser.track_rows[2])
        extra = ALBUMS[0].tracks[2]
        self.assertEqual(w.current_track, extra)
        self.assertIsNone(w.current_index)
        self.tab("Search")
        self.assertEqual(tuple(row.track for row in w.rows), TRACKS)
        self.assertEqual(w.result_count.text(), "6 tracks")
        self.assertFalse(any(row.isChecked() for row in w.rows))
        self.tab("Queue")
        self.assertEqual(w.result_count.text(), "6 tracks")
        self.assertEqual([w.rows_layout.itemAt(w.rows_layout.indexOf(w.heading_widget) + 1 + i).widget().track
                          for i in range(6)], list(TRACKS))
        self.tab("Playlists")
        self.click(w.playlists.library_rows[0])
        self.assertFalse(any(row.isChecked() for row in w.playlists.track_rows))
        self.click(w.next_button)
        self.assertEqual(w.current_track, TRACKS[0])
        w._show_track(extra)
        self.click(w.previous_button)
        self.assertEqual(w.current_track, TRACKS[-1])

    def test_album_navigation_reuses_rows_and_resets_to_library(self):
        w, browser = self.window, self.window.albums
        pool = tuple(id(row) for row in browser.track_rows)
        widget_count = len(browser.findChildren(QFrame))
        for _ in range(3):
            for album in ALBUMS:
                self.tab("Albums")
                self.assertIs(browser.currentWidget(), browser.library_page)
                browser.open_album(album.id)
                self.click(browser.track_rows[0])
                self.tab("Albums")
                self.assertIs(browser.currentWidget(), browser.library_page)
                for name in ("Search", "Playlists", "Queue"):
                    self.tab(name)
        self.assertEqual(tuple(id(row) for row in browser.track_rows), pool)
        self.assertEqual(len(browser.findChildren(QFrame)), widget_count)
        self.assertEqual(browser.count(), 2)
        self.assertEqual(w.sidebar_pages.count(), 5)

    def test_album_grid_detail_and_keyboard_at_supported_sizes(self):
        w, browser = self.window, self.window.albums
        for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
            with self.subTest(size=(width, height)):
                w.resize(width, height)
                self.tab("Albums")
                self.assertFalse(w.grab().isNull())
                self.assertEqual(browser.grid.columnCount(), 2)
                # Showing a grid resized while hidden posts a second layout pass.
                self.app.processEvents()
                first, second = browser.cards[:2]
                self.assertEqual(first.y(), second.y())
                self.assertLess(first.geometry().right(), second.x())
                self.assertLessEqual(second.geometry().right(), browser.library_scroll.viewport().width())
                for card in browser.cards:
                    self.assertGreaterEqual(card.height(), card.heightForWidth(card.width()))
                for position in range(2, len(browser.cards)):
                    self.assertLess(browser.cards[position - 2].geometry().bottom(),
                                    browser.cards[position].y())
                self.assertEqual(browser.library_scroll.horizontalScrollBar().maximum(), 0)
                first.setFocus()
                QTest.keyClick(first, Qt.Key.Key_Space)
                self.app.processEvents()
                self.assertIs(browser.currentWidget(), browser.detail_page)
                self.assertTrue(browser.header.play_button.isVisible())
                self.assertTrue(browser.back_button.isVisible())
                self.assertGreater(browser.detail_scroll.verticalScrollBar().maximum(), 0)
                self.assertEqual(browser.detail_scroll.horizontalScrollBar().maximum(), 0)
                self.assertFalse(w.grab().isNull())
                browser.detail_scroll.ensureWidgetVisible(browser.track_rows[-1])
                self.app.processEvents()
                last = browser.track_rows[-1]
                self.click(last)
                self.assertEqual(w.current_track, ALBUMS[0].tracks[-1])
                background = browser.detail_scroll.viewport().grab().toImage().pixelColor(0, 0)
                self.assertLess(max(background.red(), background.green(), background.blue()), 100)

    def open_options(self, row):
        self.click(row.options_button)
        self.assertTrue(row.menu.isVisible())
        return row.menu

    def menu_action(self, row, index):
        menu = self.open_options(row)
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton,
                         pos=menu.actionGeometry(menu.actions()[index]).center())
        self.app.processEvents()

    def test_song_menu_does_not_select_and_supports_keyboard(self):
        w = self.window
        selected, toggled = QSignalSpy(w.track_selected), QSignalSpy(w.playback_toggled)
        row = w.rows[1]
        menu = self.open_options(row)
        self.assertEqual(w.current_track, TRACKS[0])
        self.assertEqual(w.progress.value(), 102)
        self.assertFalse(row.isChecked())
        self.assertEqual([a.text() for a in menu.actions()],
                         ["Like", "Add to playlist", "", "Add to queue"])
        self.assertTrue(menu.screen().availableGeometry().contains(menu.frameGeometry()))
        QTest.keyClick(menu, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertFalse(menu.isVisible())
        row.options_button.setFocus()
        QTest.keyClick(row.options_button, Qt.Key.Key_Space)
        self.app.processEvents()
        self.assertTrue(menu.isVisible())
        QTest.keyClick(menu, Qt.Key.Key_Down)
        QTest.keyClick(menu, Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertIn(row.track.id, w.state.liked_ids)
        self.assertEqual(selected.count(), 0)
        self.assertEqual(toggled.count(), 0)

    def test_liked_empty_save_remove_and_sync_in_every_section(self):
        w = self.window
        self.tab("Liked")
        self.assertTrue(w.liked.empty.isVisible())
        self.assertEqual(w.liked.count.text(), "0 songs")
        self.tab("Search")
        self.menu_action(w.rows[0], 0)
        w.state.set_liked(TRACKS[0].id, True)
        self.assertEqual(w.state.liked_ids, [TRACKS[0].id])
        self.tab("Playlists")
        w.playlists.open_playlist(PLAYLISTS[0])
        row = w.playlists.track_rows[0]
        self.assertEqual(self.open_options(row).actions()[0].text(), "Unlike")
        row.menu.close()
        self.tab("Albums")
        w.albums.open_album(ALBUMS[0].id)
        row = w.albums.track_rows[0]
        self.assertEqual(self.open_options(row).actions()[0].text(), "Unlike")
        row.menu.close()
        self.tab("Liked")
        self.assertFalse(w.liked.empty.isVisible())
        self.assertEqual(w.liked.count.text(), "1 song")
        self.click(w.liked.rows[0])
        self.assertEqual(w.current_track, TRACKS[0])
        self.menu_action(w.liked.rows[0], 0)
        self.assertEqual(w.state.liked_ids, [])
        self.assertTrue(w.liked.empty.isVisible())
        self.tab("Search")
        self.assertEqual(self.open_options(w.rows[0]).actions()[0].text(), "Like")
        w.rows[0].menu.close()

    def test_playlist_addition_counts_duplicate_prevention_and_album_selection(self):
        w = self.window
        extra = ALBUMS[0].tracks[2]
        self.tab("Albums")
        w.albums.open_album(ALBUMS[0].id)
        row = w.albums.track_rows[2]
        menu = self.open_options(row)
        submenu = row.playlist_menu
        self.assertEqual(len(submenu.actions()), 5)
        menu.setActiveAction(menu.actions()[1])
        QTest.keyClick(menu, Qt.Key.Key_Right)
        self.app.processEvents()
        self.assertTrue(submenu.isVisible())
        self.assertTrue(submenu.screen().availableGeometry().contains(submenu.frameGeometry()))
        submenu.setActiveAction(submenu.actions()[0])
        QTest.keyClick(submenu, Qt.Key.Key_Return)
        self.app.processEvents()
        self.assertFalse(menu.isVisible())
        self.assertEqual(w.state.playlist_ids[PLAYLISTS[0].id][-1], extra.id)
        self.assertEqual(w.playlists.library_rows[0].song_count, 7)
        self.open_options(row)
        self.assertFalse(row.playlist_menu.actions()[0].isEnabled())
        row.menu.close()
        w.state.add_to_playlist(PLAYLISTS[0].id, extra.id)
        self.assertEqual(len(w.state.playlist_ids[PLAYLISTS[0].id]), 7)
        self.tab("Playlists")
        w.playlists.open_playlist(PLAYLISTS[0])
        self.app.processEvents()
        self.assertEqual(w.playlists.playlist_count.text(), "7 songs")
        added = w.playlists.track_rows[6]
        self.assertEqual(added.track, extra)
        w.playlists.detail_scroll.ensureWidgetVisible(added)
        self.click(added)
        self.assertEqual(w.current_track, extra)
        self.assertTrue(added.isChecked())
        self.assertEqual(sum(r.isChecked() for r in w.playlists.track_rows), 1)
        # Mutating the open detail updates its count and rows without navigating away.
        w.state.add_to_playlist(PLAYLISTS[0].id, ALBUMS[0].tracks[3].id)
        self.assertIs(w.playlists.currentWidget(), w.playlists.detail_page)
        self.assertEqual(w.playlists.playlist_count.text(), "8 songs")
        self.assertEqual(w.playlists.track_rows[7].track, ALBUMS[0].tracks[3])

    def test_queue_append_order_duplicates_persistence_and_like_sync(self):
        w = self.window
        self.menu_action(w.rows[2], 3)
        self.menu_action(w.rows[2], 3)
        self.tab("Albums")
        w.albums.open_album(ALBUMS[0].id)
        self.menu_action(w.albums.track_rows[2], 3)
        extra = ALBUMS[0].tracks[2]
        expected = [TRACKS[2].id, TRACKS[2].id, extra.id]
        self.assertEqual(w.state.queue_ids, expected)
        self.tab("Queue")
        self.assertEqual(w.result_count.text(), "8 tracks")
        self.assertEqual([r.track.id for r in w.queue_rows], expected)
        positions = [w.rows_layout.indexOf(r) for r in w.queue_rows]
        self.assertEqual(positions, list(range(positions[0], positions[0] + 3)))
        self.menu_action(w.queue_rows[-1], 0)
        self.assertIn(extra.id, w.state.liked_ids)
        self.tab("Liked")
        self.click(w.liked.rows[0])
        self.assertEqual(w.current_track, extra)
        self.tab("Queue")
        self.assertEqual(w.state.queue_ids, expected)
        self.assertTrue(w.queue_rows[-1].isChecked())
        self.assertEqual(self.open_options(w.queue_rows[-1]).actions()[0].text(), "Unlike")
        w.queue_rows[-1].menu.close()
        self.click(w.next_button)
        self.assertEqual(w.current_track, TRACKS[0])
        self.assertEqual(w.state.queue_ids, expected)

    def test_stable_ids_session_isolation_and_liked_rebinding(self):
        from dataclasses import replace
        from ui.mock_data import TRACKS_BY_ID
        from ui.session import SessionState
        all_tracks = [track for album in ALBUMS for track in album.tracks]
        self.assertEqual(len(TRACKS_BY_ID), len(all_tracks))
        self.assertTrue(all(track.id for track in all_tracks))
        self.assertEqual(replace(TRACKS[0], title="Renamed").id, TRACKS[0].id)
        w = self.window
        for track in TRACKS[:3]:
            w.state.set_liked(track.id, True)
        self.tab("Liked")
        self.menu_action(w.liked.rows[0], 0)
        self.assertEqual(w.liked.rows[0].track, TRACKS[1])
        self.menu_action(w.liked.rows[0], 0)
        self.assertEqual(w.state.liked_ids, [TRACKS[2].id])
        fresh = SessionState()
        self.assertEqual(fresh.liked_ids, [])
        self.assertEqual(fresh.queue_ids, [])
        self.assertEqual(len(fresh.playlist_ids[PLAYLISTS[0].id]), 6)

    def test_five_tabs_menus_and_liked_layout_at_supported_sizes(self):
        w = self.window
        for album in ALBUMS:
            for track in album.tracks:
                w.state.set_liked(track.id, True)
        for width, height in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(width, height)
            for name in ("Search", "Playlists", "Albums", "Queue", "Liked"):
                self.tab(name)
            self.app.processEvents()
            self.assertEqual(w.size().toTuple(), (width, height))
            self.assertEqual(w.liked.count.text(), f"{len(TRACKS_BY_ID)} songs")
            self.assertGreater(w.liked.scroll.verticalScrollBar().maximum(), 0)
            self.assertEqual(w.liked.scroll.horizontalScrollBar().maximum(), 0)
            buttons = w.tabs.buttons()
            for left, right in zip(buttons, buttons[1:]):
                self.assertLess(left.geometry().right(), right.x())
                self.assertGreaterEqual(left.width(), left.fontMetrics().horizontalAdvance(left.text()))
            self.assertLessEqual(buttons[-1].geometry().right(), buttons[-1].parentWidget().width())
            row = w.liked.rows[0]
            self.assertTrue(row.rect().contains(row.options_button.geometry()))
            for _ in range(3):
                menu = self.open_options(row)
                QTest.keyClick(menu, Qt.Key.Key_Escape)
                self.app.processEvents()
            self.open_options(row)
            self.tab("Search")
            self.assertFalse(row.menu.isVisible())
            self.tab("Liked")
            self.assertFalse(w.grab().isNull())

    def test_queue_has_no_search_or_hidden_search_filter(self):
        from PySide6.QtWidgets import QScrollArea

        w = self.window
        area = w.catalog_page.findChild(QScrollArea)
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            self.tab("Search")
            w.search.setText("no-matching-song")
            self.assertTrue(w.search.isVisible())
            self.assertTrue(w.empty.isVisible())
            self.app.processEvents()
            search_list_y = area.y()
            self.tab("Queue")
            self.app.processEvents()
            self.assertFalse(w.search_box.isVisible())
            self.assertFalse(w.search.isVisible())
            self.assertLess(area.y(), search_list_y)
            self.assertFalse(w.empty.isVisible())
            self.assertEqual(sum(not row.isHidden() for row in w.rows), 5)
            before = len(w.state.queue_ids)
            self.menu_action(w.rows[1], 3)
            self.assertEqual(len(w.state.queue_ids), before + 1)
            self.assertTrue(w.queue_rows[-1].isVisible())
            self.assertEqual(w.result_count.text(), f"{6 + before} tracks")
            self.assertEqual(area.horizontalScrollBar().maximum(), 0)
            self.tab("Search")
            self.assertTrue(w.search.isVisible())
            self.assertEqual(w.search.text(), "no-matching-song")
            self.assertTrue(w.empty.isVisible())

    def capture_row_text(self, row):
        """Observe actual paint output, so a missing/replaced duration fails the test."""
        from PySide6.QtGui import QPainter

        calls = []

        class RecordingPainter(QPainter):
            def __init__(self, device):
                super().__init__(device)
                self.is_row = device is row

            def drawText(self, *args):
                if self.is_row:
                    calls.append((args[0], args[-1]))
                return super().drawText(*args)

        with patch("ui.widgets.QPainter", RecordingPainter), patch("ui.search.QPainter", RecordingPainter):
            image = row.grab().toImage()
        return image, calls

    def test_search_paints_durations_in_all_playback_and_like_states(self):
        from ui.mock_data import time_text

        w = self.window
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            self.app.processEvents()
            columns = []
            for row in [w.top_rows[0], *w.rows]:
                for selected, playing, liked in ((False, True, False), (True, True, False),
                                                (True, True, True), (True, False, True)):
                    row.setChecked(selected)
                    row.playing = playing
                    w.state.set_liked(row.track.id, liked)
                    _, calls = self.capture_row_text(row)
                    durations = [rect for rect, text in calls if text == time_text(row.track.seconds)]
                    self.assertEqual(len(durations), 1)
                    self.assertLess(durations[0].right(), row.options_button.x())
                    columns.append(durations[0].x())
                w.state.set_liked(row.track.id, False)
            self.assertEqual(len(set(columns)), 1)
            for row in w.search_result_rows:
                from PySide6.QtWidgets import QToolButton
                _, calls = self.capture_row_text(row)
                self.assertFalse(row.findChildren(QToolButton))
                self.assertFalse(any(text == time_text(track.seconds) for _, text in calls for track in TRACKS))

    def test_heart_renders_beside_short_and_elided_titles_in_all_sections(self):
        from dataclasses import replace
        from ui.mock_data import time_text

        w = self.window
        track = TRACKS[1]
        w.state.add_to_queue(track.id)
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            for section in ("Search", "Playlists", "Albums", "Queue", "Liked"):
                w.state.set_liked(track.id, True)
                self.tab(section)
                if section == "Playlists":
                    w.playlists.open_playlist(PLAYLISTS[1])
                    row = w.playlists.track_rows[0]
                elif section == "Albums":
                    w.albums.open_album(track.album_id)
                    row = w.albums.track_rows[0]
                elif section == "Queue":
                    row = w.queue_rows[0]
                elif section == "Liked":
                    row = w.liked.rows[0]
                else:
                    row = w.rows[1]
                self.app.processEvents()
                self.assertEqual(self.open_options(row).actions()[0].text(), "Unlike")
                row.menu.close()
                self.assertEqual(row.height(), 68)
                options_rect = row.options_button.geometry()
                for title in ("Blue", "A very long song title that must leave space for its heart " * 5):
                    row.track = replace(track, title=title)
                    image, calls = self.capture_row_text(row)
                    title_rect, shown_title = calls[1] if row.track_number is not None else calls[0]
                    duration_rect = next(rect for rect, text in calls if text == time_text(track.seconds))
                    if title != "Blue":
                        self.assertIn("…", shown_title)
                        self.assertNotEqual(title, shown_title)
                    # Find the actual gold heart pixels in the title line; excludes cover/number.
                    points = []
                    for y in range(14, 36):
                        for x in range(int(title_rect.left()), int(duration_rect.left())):
                            color = image.pixelColor(x, y)
                            if color.red() - color.green() > 15 and color.green() - color.blue() > 20 and color.green() > 110:
                                points.append((x, y))
                    self.assertTrue(points, (section, size, title))
                    xs, ys = zip(*points)
                    self.assertLessEqual(max(xs) - min(xs), 12)
                    self.assertLessEqual(max(ys) - min(ys), 12)
                    self.assertLess(max(xs), duration_rect.left())
                    self.assertLess(abs((min(ys) + max(ys)) / 2 - title_rect.center().y()), 3)
                    if title == "Blue":
                        self.assertLess(min(xs) - title_rect.left(), 50)
                    self.assertEqual(row.options_button.geometry(), options_rect)
                row.track = track
                liked_image, _ = self.capture_row_text(row)
                self.menu_action(row, 0)
                self.assertNotIn(track.id, w.state.liked_ids)
                if section != "Liked":
                    unliked_image, _ = self.capture_row_text(row)
                    self.assertNotEqual(liked_image.copy(74, 14, row.width() - 168, 22),
                                        unliked_image.copy(74, 14, row.width() - 168, 22))
                    self.assertEqual(self.open_options(row).actions()[0].text(), "Like")
                    row.menu.close()
                else:
                    self.assertTrue(w.liked.empty.isVisible())

    def search_result(self, kind, entity_id):
        row = next(row for row in self.window.search_result_rows
                   if row.kind == kind and row.entity.id == entity_id)
        self.window.catalog_scroll.ensureWidgetVisible(row)
        self.app.processEvents()
        self.assertTrue(row.isVisible())
        return row

    def test_search_opens_every_album_without_playing_and_reuses_detail(self):
        w = self.window
        self.click(w.play_button)
        w.progress.setValue(120)
        selected, toggled = QSignalSpy(w.track_selected), QSignalSpy(w.playback_toggled)
        detail = w.albums.detail_page
        for album in ALBUMS:
            w.search.setText(album.name)
            row = self.search_result("album", album.id)
            self.click(row)
            self.assertIs(w.sidebar_pages.currentWidget(), w.albums)
            self.assertIs(w.albums.currentWidget(), detail)
            self.assertEqual(w.albums.back_button.text(), "‹   Search results")
            self.assertEqual(w.albums.header.title.text(), album.name)
            self.assertEqual(w.albums.header.artist.text(), album.artist)
            self.assertIn(str(album.year), w.albums.header.metadata.text())
            self.assertEqual(tuple(r.track for r in w.albums.track_rows if not r.isHidden()), album.tracks)
            self.assertEqual(w.progress.value(), 120)
            self.assertFalse(w.is_playing)
            self.assertEqual(selected.count(), 0)
            self.assertEqual(toggled.count(), 0)
            self.click(w.albums.back_button)
            self.app.processEvents()
            self.assertIs(w.sidebar_pages.currentWidget(), w.catalog_page)
            self.assertEqual(w.search.text(), album.name)
            self.assertTrue(row.isVisible())
            self.assertEqual(w.search_history, [])
        self.click(self.search_result("album", ALBUMS[-1].id))
        self.click(w.albums.track_rows[1])
        self.assertIs(w.current_track, ALBUMS[-1].tracks[1])
        self.assertIs(w.turntable.track, w.current_track)
        self.assertFalse(w.is_playing)
        self.click(w.albums.header.play_button)
        self.assertIs(w.current_track, ALBUMS[-1].tracks[0])
        self.assertTrue(w.is_playing)
        self.assertEqual(toggled.count(), 1)
        self.assertEqual(selected.count(), 2)

    def test_search_artist_profiles_use_shared_entities_and_circular_portraits(self):
        from ui.mock_data import ARTISTS, TRACKS_BY_ID
        w = self.window
        selected, toggled = QSignalSpy(w.track_selected), QSignalSpy(w.playback_toggled)
        for artist in ARTISTS:
            w.search.setText(artist.name)
            self.click(self.search_result("artist", artist.id))
            profile = w.artist_profile
            self.assertIs(w.sidebar_pages.currentWidget(), profile)
            self.assertEqual(profile.name.text(), artist.name)
            rows = [r for r in profile.track_rows if not r.isHidden()]
            self.assertEqual(tuple(r.track.id for r in rows), artist.track_ids)
            self.assertTrue(all(r.track is TRACKS_BY_ID[r.track.id] for r in rows))
            self.assertEqual(tuple(c.album.id for c in profile.album_cards if not c.isHidden()), artist.album_ids)
            for album_id in artist.album_ids:
                album = ALBUMS_BY_ID[album_id]
                self.assertEqual(album.artist, artist.name)
                self.assertTrue(all(t.id in artist.track_ids for t in album.tracks))
            portrait = profile.portrait.pixmap().toImage()
            self.assertEqual(portrait.pixelColor(0, 0).alpha(), 0)
            self.assertGreater(portrait.pixelColor(41, 41).alpha(), 0)
            self.assertEqual(selected.count(), 0)
            self.assertEqual(toggled.count(), 0)
            self.click(profile.back_button)
            self.app.processEvents()
            self.assertEqual(w.search.text(), artist.name)

    def test_artist_album_back_restores_both_scroll_positions_and_results(self):
        from ui.mock_data import ARTISTS
        w = self.window
        w.resize(1120, 760)
        w.search.setText("the")
        row = self.search_result("artist", ARTISTS[0].id)
        row.setFocus()
        self.app.processEvents()
        results = [r.entity.id for r in w.search_result_rows if not r.isHidden()]
        result_scroll = w.catalog_scroll.verticalScrollBar().value()
        self.click(row)
        profile = w.artist_profile
        card = next(c for c in profile.album_cards if not c.isHidden())
        profile.scroll.ensureWidgetVisible(card)
        self.app.processEvents()
        card.setFocus()
        artist_scroll = profile.scroll.verticalScrollBar().value()
        self.assertGreater(artist_scroll, 0)
        self.click(card)
        self.assertEqual(w.albums.back_button.text(), "‹   Artist profile")
        self.assertEqual(len(w.search_history), 2)
        self.click(w.albums.track_rows[2])
        self.assertIs(w.current_track, ALBUMS[0].tracks[2])
        self.click(w.albums.back_button)
        self.app.processEvents()
        self.assertIs(w.sidebar_pages.currentWidget(), profile)
        self.assertEqual(profile.scroll.verticalScrollBar().value(), artist_scroll)
        self.assertIs(w.focusWidget(), card)
        self.assertTrue(profile.track_rows[2].isChecked())
        self.click(profile.back_button)
        self.app.processEvents()
        self.assertEqual(w.search.text(), "the")
        self.assertEqual([r.entity.id for r in w.search_result_rows if not r.isHidden()], results)
        self.assertEqual(w.catalog_scroll.verticalScrollBar().value(), result_scroll)
        self.assertIs(w.focusWidget(), row)
        self.assertEqual(w.search_history, [])

    def test_artist_and_search_album_song_actions_share_session_state(self):
        from ui.mock_data import ARTISTS
        w = self.window
        w.search.setText(ARTISTS[0].name)
        self.click(self.search_result("artist", ARTISTS[0].id))
        profile = w.artist_profile
        row = profile.track_rows[2]
        track = row.track
        selected = QSignalSpy(w.track_selected)
        self.menu_action(row, 0)
        self.assertIn(track.id, w.state.liked_ids)
        self.menu_action(row, 3)
        menu = self.open_options(row)
        row.playlist_menu.actions()[4].trigger()
        menu.close()
        self.assertEqual(selected.count(), 0)
        self.assertEqual(w.state.queue_ids, [track.id])
        self.assertEqual(w.state.playlist_ids[PLAYLISTS[4].id][-1], track.id)
        self.click(row)
        self.assertIs(w.current_track, track)
        self.click(profile.album_cards[0])
        self.assertEqual(self.open_options(w.albums.track_rows[2]).actions()[0].text(), "Unlike")
        w.albums.track_rows[2].menu.close()
        self.menu_action(w.albums.track_rows[2], 0)
        self.assertNotIn(track.id, w.state.liked_ids)
        self.menu_action(w.albums.track_rows[2], 3)
        self.assertEqual(w.state.queue_ids, [track.id, track.id])
        self.click(w.albums.back_button)
        self.assertEqual(self.open_options(row).actions()[0].text(), "Like")
        row.menu.close()
        self.menu_action(row, 0)
        self.tab("Liked")
        self.assertIs(w.liked.rows[0].track, track)
        self.tab("Playlists")
        w.playlists.open_playlist(PLAYLISTS[4])
        self.assertIs(w.playlists.track_rows[2].track, track)
        self.tab("Queue")
        self.assertTrue(all(r.track is track for r in w.queue_rows))

    def test_search_empty_artist_and_single_empty_section(self):
        from dataclasses import replace
        from ui.mock_data import ARTISTS, ARTISTS_BY_ID
        w = self.window
        artist = ARTISTS[-1]
        w.search.setText(artist.name)
        self.assertEqual(w.result_count.text(), "0 tracks")
        self.assertFalse(w.empty.isVisible())  # An artist result still exists.
        self.click(self.search_result("artist", artist.id))
        profile = w.artist_profile
        self.assertTrue(profile.empty_songs.isVisible())
        self.assertTrue(profile.empty_albums.isVisible())
        self.assertFalse(any(r.isVisible() for r in profile.track_rows))
        self.assertFalse(any(c.isVisible() for c in profile.album_cards))
        # A profile may have a known song without a known album entry.
        with patch.dict(ARTISTS_BY_ID, {artist.id: replace(artist, track_ids=(TRACKS[0].id,))}):
            profile.open_artist(artist.id)
            self.assertFalse(profile.empty_songs.isVisible())
            self.assertTrue(profile.empty_albums.isVisible())
            self.click(profile.track_rows[0])
            self.assertIs(w.current_track, TRACKS[0])
        self.click(profile.back_button)
        w.search.setText("not-an-artist-or-record")
        self.assertTrue(w.empty.isVisible())

    def test_search_navigation_reuse_and_switching_tabs_reset_back_context(self):
        from ui.mock_data import ARTISTS
        w = self.window
        detail = w.albums.detail_page
        for _ in range(3):
            for artist in ARTISTS[:5]:
                self.tab("Search")
                w.search.setText(artist.name)
                self.click(self.search_result("artist", artist.id))
                card = next(c for c in w.artist_profile.album_cards if not c.isHidden())
                self.click(card)
                self.assertIs(w.albums.detail_page, detail)
                self.tab("Albums")
                self.assertEqual(w.search_history, [])
                self.click(w.albums.cards[0])
                self.assertEqual(w.albums.back_button.text(), "‹   Your Albums")
                self.click(w.albums.back_button)
                self.assertIs(w.albums.currentWidget(), w.albums.library_page)
                for tab in ("Playlists", "Queue", "Liked", "Search"):
                    self.tab(tab)
                self.assertIs(w.sidebar_pages.currentWidget(), w.catalog_page)
                self.assertEqual(w.search.text(), artist.name)
        self.assertEqual(len(w.artist_profile.track_rows), 12)
        self.assertEqual(len(w.artist_profile.album_cards), len(ALBUMS))
        self.assertEqual(w.sidebar_pages.count(), 5)
        # A queued back restoration must not affect a subsequent tab change.
        self.click(self.search_result("artist", ARTISTS[4].id))
        w.artist_profile.back_button.click()
        next(b for b in w.tabs.buttons() if b.text() == "Queue").click()
        self.app.processEvents()
        self.assertEqual(w.section, "Queue")
        self.assertFalse(w.search.isVisible())

    def test_search_exploration_keyboard_and_layout_at_supported_sizes(self):
        from ui.mock_data import ARTISTS
        w = self.window
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            self.tab("Search")
            w.search.setText(ARTISTS[0].name)
            self.app.processEvents()
            row = self.search_result("artist", ARTISTS[0].id)
            row.setFocus()
            QTest.keyClick(row, Qt.Key.Key_Space)
            self.app.processEvents()
            profile = w.artist_profile
            self.assertIs(w.sidebar_pages.currentWidget(), profile)
            self.assertEqual(w.size().toTuple(), size)
            self.assertEqual(profile.scroll.verticalScrollBar().value(), 0)
            self.assertEqual(profile.scroll.horizontalScrollBar().maximum(), 0)
            self.assertGreater(profile.scroll.verticalScrollBar().maximum(), 0)
            self.assertFalse(w.grab().isNull())
            card = profile.album_cards[0]
            profile.scroll.ensureWidgetVisible(card)
            self.app.processEvents()
            self.assertLessEqual(card.width(), profile.scroll.viewport().width() / 2)
            self.assertGreaterEqual(card.height(), card.heightForWidth(card.width()))
            card.setFocus()
            QTest.keyClick(card, Qt.Key.Key_Space)
            self.app.processEvents()
            self.assertIs(w.sidebar_pages.currentWidget(), w.albums)
            self.assertEqual(w.albums.detail_scroll.horizontalScrollBar().maximum(), 0)
            self.assertTrue(w.albums.header.play_button.isVisible())
            self.assertFalse(w.grab().isNull())
            self.click(w.albums.back_button)
            self.click(profile.back_button)
            self.click(self.search_result("artist", ARTISTS[0].id))
            self.app.processEvents()
            self.assertEqual(profile.scroll.verticalScrollBar().value(), 0)
            self.assertIs(w.focusWidget(), profile.back_button)
            self.click(profile.back_button)

    def test_save_remove_album_syncs_without_changing_songs_or_playback(self):
        from ui.mock_data import ARTISTS
        w = self.window
        album = ALBUMS_BY_ID["moonlit-water"]
        self.assertNotIn(album.id, w.state.saved_album_ids)
        w.state.set_liked(album.tracks[0].id, True)
        w.state.add_to_playlist(PLAYLISTS[0].id, album.tracks[0].id)
        likes = list(w.state.liked_ids)
        playlist = list(w.state.playlist_ids[PLAYLISTS[0].id])
        selected, toggled = QSignalSpy(w.track_selected), QSignalSpy(w.playback_toggled)
        saved = QSignalSpy(w.state.saved_albums_changed)
        w.search.setText(album.name)
        self.click(self.search_result("album", album.id))
        self.assertEqual(w.albums.save_button.text(), "Save album")
        self.click(w.albums.save_button)
        w.state.set_album_saved(album.id, True)
        self.assertEqual(saved.count(), 1)
        self.assertEqual(w.state.saved_album_ids.count(album.id), 1)
        self.assertEqual(w.albums.save_button.text(), "Remove from library")
        self.tab("Albums")
        card = next(card for card in w.albums.cards if card.album.id == album.id)
        self.assertTrue(card.isVisible())
        self.assertEqual(w.albums.library_count.text(), "6 albums")
        self.click(card)
        self.click(w.albums.save_button)
        self.assertEqual(w.albums.save_button.text(), "Save album")
        self.assertNotIn(album.id, [c.album.id for c in w.albums.cards])
        self.assertIs(w.albums.currentWidget(), w.albums.detail_page)
        self.tab("Search")
        self.click(self.search_result("album", album.id))
        self.assertEqual(w.albums.save_button.text(), "Save album")
        self.click(w.albums.back_button)
        w.search.setText(ARTISTS[3].name)
        self.click(self.search_result("artist", ARTISTS[3].id))
        card = next(c for c in w.artist_profile.album_cards if c.album.id == album.id)
        self.assertFalse(card.isHidden())
        self.click(card)
        self.assertEqual(w.albums.save_button.text(), "Save album")
        self.click(w.albums.save_button)
        self.assertEqual(w.albums.save_button.text(), "Remove from library")
        self.assertEqual(w.state.liked_ids, likes)
        self.assertEqual(w.state.playlist_ids[PLAYLISTS[0].id], playlist)
        self.assertEqual(selected.count(), 0)
        self.assertEqual(toggled.count(), 0)
        self.assertEqual(w.progress.value(), 102)

    def test_empty_saved_album_library_and_resave_keeps_order(self):
        w = self.window
        self.tab("Albums")
        for album_id in list(w.state.saved_album_ids):
            w.albums.open_album(album_id)
            self.click(w.albums.save_button)
            self.click(w.albums.back_button)
        self.assertTrue(w.albums.empty_library.isVisible())
        self.assertEqual(w.albums.library_count.text(), "0 albums")
        self.assertEqual(w.albums.cards, [])
        self.assertFalse(any(c.isVisible() for c in w.albums.all_cards))
        for album in (ALBUMS[3], ALBUMS[0]):
            self.tab("Search")
            w.search.setText(album.name)
            self.click(self.search_result("album", album.id))
            self.click(w.albums.save_button)
        self.tab("Albums")
        self.assertFalse(w.albums.empty_library.isVisible())
        self.assertEqual([c.album.id for c in w.albums.cards], [ALBUMS[3].id, ALBUMS[0].id])
        first, second = w.albums.cards
        self.assertEqual(first.y(), second.y())
        self.assertLess(first.geometry().right(), second.x())

    def create_playlist_from_ui(self, name):
        self.tab("Playlists")
        browser = self.window.playlists
        self.click(browser.new_button)
        browser.name_input.setText(name)
        self.click(browser.create_button)
        self.assertFalse(browser.composer.isVisible())
        return browser.library_rows[-1].playlist

    def test_new_playlist_validation_cancel_and_single_confirmation(self):
        w, browser = self.window, self.window.playlists
        self.tab("Playlists")
        created = QSignalSpy(w.state.playlist_created)
        self.click(browser.new_button)
        self.assertIs(w.focusWidget(), browser.name_input)
        for name in ("", "   ", "x" * 81):
            browser.name_input.setText(name)
            self.click(browser.create_button)
            self.assertTrue(browser.composer.isVisible())
            self.assertTrue(browser.creation_error.text())
            self.assertEqual(created.count(), 0)
        self.click(browser.cancel_button)
        self.assertEqual(len(w.state.playlists), 5)
        self.assertFalse(browser.composer.isVisible())
        self.click(browser.new_button)
        browser.name_input.setText("   Jazz & Soul   ")
        QTest.keyClick(browser.name_input, Qt.Key.Key_Return)
        browser.create_button.click()  # An extra confirmation on the now-hidden form is ignored.
        self.app.processEvents()
        self.assertEqual(created.count(), 1)
        playlist = browser.library_rows[-1].playlist
        self.assertEqual(playlist.name, "Jazz & Soul")
        self.assertEqual(w.state.playlist_ids[playlist.id], [])
        self.assertEqual(browser.library_count.text(), "6 playlists")
        duplicate_name = self.create_playlist_from_ui("Jazz & Soul")
        self.assertNotEqual(playlist.id, duplicate_name.id)
        self.assertEqual(created.count(), 2)
        self.click(browser.new_button)
        browser.name_input.setText("Unconfirmed")
        self.tab("Search")
        self.tab("Playlists")
        self.assertFalse(browser.composer.isVisible())
        self.assertEqual(created.count(), 2)
        # The model also validates direct callers and separates sessions.
        from ui.session import SessionState
        fresh = SessionState()
        for invalid in ("", "\t\n", "y" * 81):
            with self.assertRaises(ValueError):
                fresh.create_playlist(invalid)
        self.assertEqual(len(fresh.playlists), 5)
        self.assertNotIn(playlist.id, fresh.playlists)
        self.assertEqual(fresh.saved_album_ids, list(INITIAL_SAVED_ALBUM_IDS))

    def test_new_empty_playlist_and_dynamic_menu_then_play_album_only_track(self):
        w = self.window
        # This menu exists before the new playlist and must refresh on its next opening.
        menu = self.open_options(w.rows[0])
        self.assertEqual(len(w.rows[0].playlist_menu.actions()), 5)
        menu.close()
        playlist = self.create_playlist_from_ui("Evening records")
        browser = w.playlists
        self.click(browser.library_rows[-1])
        self.assertEqual(browser.playlist_title.text(), playlist.name)
        self.assertEqual(browser.playlist_count.text(), "0 songs")
        self.assertTrue(browser.empty_playlist.isVisible())
        self.assertFalse(browser.play_button.isVisible())
        self.assertFalse(browser.play_button.isEnabled())
        self.assertFalse(browser.cover.pixmap().isNull())
        selected, toggled = QSignalSpy(w.track_selected), QSignalSpy(w.playback_toggled)
        browser._request_play()
        self.assertEqual(selected.count(), 0)
        self.tab("Search")
        self.open_options(w.rows[0])
        self.assertEqual(len(w.rows[0].playlist_menu.actions()), 6)
        self.assertIn(playlist.id, [a.data() for a in w.rows[0].playlist_menu.actions()])
        w.rows[0].menu.close()
        w.search.setText("Moonlit Water")
        self.click(self.search_result("album", "moonlit-water"))
        row = w.albums.track_rows[0]
        extra = row.track
        menu = self.open_options(row)
        action = next(a for a in row.playlist_menu.actions() if a.data() == playlist.id)
        action.trigger()
        menu.close()
        self.open_options(row)
        action = next(a for a in row.playlist_menu.actions() if a.data() == playlist.id)
        self.assertFalse(action.isEnabled())
        row.menu.close()
        w.state.add_to_playlist(playlist.id, extra.id)
        self.assertEqual(w.state.playlist_ids[playlist.id], [extra.id])
        self.assertEqual(selected.count(), 0)
        self.assertEqual(toggled.count(), 0)
        self.tab("Playlists")
        self.assertEqual(browser.library_rows[-1].song_count, 1)
        self.click(browser.library_rows[-1])
        self.assertFalse(browser.empty_playlist.isVisible())
        self.assertTrue(browser.play_button.isVisible())
        self.assertIs(browser.track_rows[0].track, extra)
        self.click(w.play_button)
        self.assertFalse(w.is_playing)
        self.click(browser.play_button)
        self.assertIs(w.current_track, extra)
        self.assertTrue(w.is_playing)
        self.assertIsNone(w.current_index)
        w.state.add_to_playlist(playlist.id, TRACKS[2].id)
        self.assertEqual(browser.playlist_count.text(), "2 songs")
        self.assertIs(browser.track_rows[1].track, TRACKS[2])
        self.click(browser.track_rows[1])
        self.assertEqual(w.current_index, 2)
        self.assertEqual(w.state.playlist_ids[playlist.id], [extra.id, TRACKS[2].id])

    def test_artist_song_can_be_added_to_new_playlist_with_duplicate_names(self):
        from ui.mock_data import ARTISTS
        w = self.window
        first = self.create_playlist_from_ui("My collection")
        second = self.create_playlist_from_ui("My collection")
        self.tab("Search")
        w.search.setText(ARTISTS[0].name)
        self.click(self.search_result("artist", ARTISTS[0].id))
        row = w.artist_profile.track_rows[2]
        menu = self.open_options(row)
        action = next(a for a in row.playlist_menu.actions() if a.data() == second.id)
        action.trigger()
        menu.close()
        self.assertEqual(w.state.playlist_ids[first.id], [])
        self.assertEqual(w.state.playlist_ids[second.id], [row.track.id])
        self.menu_action(row, 0)
        self.menu_action(row, 3)
        self.assertIn(row.track.id, w.state.liked_ids)
        self.assertEqual(w.state.queue_ids[-1], row.track.id)

    def test_album_save_and_playlist_form_layout_at_supported_sizes(self):
        w, browser = self.window, self.window.playlists
        for size in ((1120, 760), (1400, 900), (1680, 1050)):
            w.resize(*size)
            self.tab("Search")
            w.search.setText("Moonlit Water")
            self.click(self.search_result("album", "moonlit-water"))
            for _ in range(2):
                button = w.albums.save_button
                self.assertTrue(button.isVisible())
                self.assertTrue(button.parentWidget().rect().contains(button.geometry()))
                self.assertLess(w.albums.header.play_button.geometry().bottom(), button.y())
                self.assertEqual(w.size().toTuple(), size)
                self.click(button)
            self.tab("Playlists")
            self.click(browser.new_button)
            self.assertTrue(browser.composer.isVisible())
            self.assertEqual(w.size().toTuple(), size)
            for button in (browser.create_button, browser.cancel_button):
                self.assertTrue(browser.composer.rect().contains(button.geometry()))
            browser.name_input.setText("W" * 80)
            self.click(browser.create_button)
            self.click(browser.library_rows[-1])
            self.app.processEvents()
            self.assertEqual(browser.playlist_title.text(), "W" * 80)
            self.assertEqual(w.size().toTuple(), size)
            self.assertEqual(browser.detail_scroll.horizontalScrollBar().maximum(), 0)
            self.assertTrue(browser.empty_playlist.isVisible())
            self.assertFalse(w.grab().isNull())


if __name__ == "__main__":
    unittest.main()
