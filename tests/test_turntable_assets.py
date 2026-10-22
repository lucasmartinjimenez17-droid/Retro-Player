"""Photographic assets, composition, fallback and DPR regression checks."""
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QAbstractAnimation, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from ui.mock_data import TRACKS
from ui.turntable_assets import (
    ASSET_DIRECTORY, LAYER_NAMES, LayeredTurntable, cover_source_rect, load_artwork,
)
from ui.widgets import Turntable, cover_art, deck_texture


class TurntableAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owns_app = QApplication.instance() is None
        cls.app = QApplication.instance() or QApplication([])
        # Keep fixtures inside the workspace; Windows sandbox temp ACLs can
        # allow mkdtemp while rejecting writes to files inside that directory.
        cls.fixture_parent = Path(__file__).resolve().parent / "__pycache__"
        cls.fixture_parent.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cover_art.cache_clear()
        deck_texture.cache_clear()
        if cls.owns_app:
            delete(cls.app)

    def setUp(self):
        self.deck = Turntable()
        self.deck.resize(820, 650)
        self.addCleanup(delete, self.deck)

    def test_complete_pack_real_alpha_and_shared_decode(self):
        pack, error = load_artwork()
        self.assertIsNone(error)
        self.assertEqual(set(pack.images), set(LAYER_NAMES))
        self.assertIs(load_artwork()[0], pack)
        for name, im in pack.images.items():
            self.assertTrue(im.hasAlphaChannel(), name)
            self.assertEqual(im.pixelColor(0, 0).alpha(), 0, name)
            # Object/shadow and transparency must coexist within each image.
            alphas = {im.pixelColor(x, y).alpha()
                      for x in range(0, im.width(), 7) for y in range(0, im.height(), 7)}
            self.assertIn(0, alphas, name)
            self.assertGreater(max(alphas), 245, name)
            self.assertTrue(any(0 < alpha < 245 for alpha in alphas), name)

    def test_corrupt_missing_and_opaque_assets_use_complete_fallback(self):
        with tempfile.TemporaryDirectory(prefix="assets-", dir=self.fixture_parent) as directory:
            root = Path(directory).resolve()
            self.assertEqual(root.parent, self.fixture_parent)
            for broken in ("missing-metadata", "missing-vinyl", "corrupt-arm", "opaque-vinyl"):
                with self.subTest(broken=broken):
                    for source in ASSET_DIRECTORY.iterdir():
                        if source.suffix in (".json", ".png"):
                            shutil.copy2(source, root / source.name)
                    if broken == "missing-metadata":
                        (root / "metadata.json").unlink()
                    elif broken == "missing-vinyl":
                        (root / "vinyl.png").unlink()
                    elif broken == "corrupt-arm":
                        (root / "tonearm.png").write_bytes(b"not a PNG")
                    else:
                        opaque = QImage(1254, 1254, QImage.Format.Format_ARGB32)
                        opaque.fill(QColor("#777777"))
                        self.assertTrue(opaque.save(str(root / "vinyl.png")))
                    load_artwork.cache_clear()
                    deck = Turntable(asset_directory=root)
                    try:
                        self.assertIsNone(deck._asset_art)
                        self.assertIn("unavailable", deck.asset_error)
                        deck.resize(820, 650)
                        first = deck.grab().toImage()
                        self.assertFalse(first.isNull())
                        self.assertEqual(set(deck._layers), {"base", "record", "label", "arm"})
                        deck.set_track(TRACKS[1])
                        self.assertNotEqual(first, deck.grab().toImage())
                    finally:
                        delete(deck)
        load_artwork.cache_clear()

    def test_invalid_metadata_falls_back_before_paint(self):
        with tempfile.TemporaryDirectory(prefix="assets-", dir=self.fixture_parent) as directory:
            root = Path(directory).resolve()
            self.assertEqual(root.parent, self.fixture_parent)
            for source in ASSET_DIRECTORY.glob("*.png"):
                shutil.copy2(source, root / source.name)
            original = (ASSET_DIRECTORY / "metadata.json").read_text(encoding="utf-8")
            for invalid in ("version", "outside", "nan", "missing-layer", "viewport", "split"):
                with self.subTest(invalid=invalid):
                    data = json.loads(original)
                    if invalid == "version":
                        data["version"] = 100
                    elif invalid == "outside":
                        data["arm_pivot"] = [900, 100]
                    elif invalid == "nan":
                        data["record_center"] = [float("nan"), 300]
                    elif invalid == "viewport":
                        data["viewport"] = [-5, 0, 820, 650]
                    elif invalid == "split":
                        data["transport_split"] = 640
                    else:
                        del data["layers"]["tonearm"]
                    (root / "metadata.json").write_text(json.dumps(data), encoding="utf-8")
                    load_artwork.cache_clear()
                    pack, error = load_artwork(root)
                    self.assertIsNone(pack)
                    self.assertIsNotNone(error)
        load_artwork.cache_clear()

    def test_song_change_updates_printed_label_without_reloading_images(self):
        deck = self.deck
        deck.grab()
        art = deck._asset_art
        static_keys = {name: buf.cacheKey() for name, buf in art.buffers.items()}
        before = art.label.toImage()
        with patch("ui.turntable_assets.QImageReader", side_effect=AssertionError("Repeated I/O")):
            for _ in range(4):
                deck.grab()
            self.assertEqual(before, art.label.toImage())
            deck.set_track(TRACKS[1])
            deck.grab()
            self.assertNotEqual(before, art.label.toImage())
            deck.playing = False
            deck.grab()
            deck.playing = True
            deck.grab()
        self.assertEqual(static_keys, {name: buf.cacheKey() for name, buf in art.buffers.items()})
        self.assertIs(deck.track, TRACKS[1])
        self.assertFalse(deck.findChildren(QTimer))
        self.assertFalse(deck.findChildren(QAbstractAnimation))

    def test_label_is_circular_and_non_square_cover_is_not_stretched(self):
        self.assertEqual(cover_source_rect(QSize(600, 300)), QRectF(150, 0, 300, 300))
        self.assertEqual(cover_source_rect(QSize(300, 600)), QRectF(0, 150, 300, 300))
        self.deck.grab()
        label = self.deck._asset_art.label.toImage()
        self.assertEqual(label.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(label.pixelColor(label.width() - 1, label.height() - 1).alpha(), 0)
        self.assertGreater(label.pixelColor(label.width() // 2, label.height() // 4).alpha(), 245)

    def test_approved_arm_has_no_baked_background_or_glow(self):
        arm = self.deck._asset_art.artwork.images["tonearm"]
        # These locations were gold/black in the generation preview but must
        # contribute no pixels when placed over the record or navy surface.
        for x, y in ((500, 600), (400, 400), (1023, 0), (0, 1535)):
            self.assertEqual(arm.pixelColor(x, y).getRgb(), (0, 0, 0, 0))
        self.assertGreater(arm.pixelColor(770, 328).alpha(), 245)

    def test_viewport_transform_is_uniform_at_fractional_and_high_dpr(self):
        art = self.deck._asset_art
        self.assertEqual(self.deck.grab().toImage().pixelColor(0, 0),
                         QColor(art.metadata["background"]))
        v = QRectF(*art.metadata["viewport"])
        for size in (QSize(668, 558), QSize(874, 700), QSize(1154, 850)):
            scale, origin = art.layout_transform(size)
            mapped = QRectF(origin.x() + v.x() * scale, origin.y() + v.y() * scale,
                            v.width() * scale, v.height() * scale)
            self.assertAlmostEqual(mapped.center().x(), size.width() / 2)
            self.assertAlmostEqual(mapped.bottom(), size.height())
            self.assertGreaterEqual(mapped.top(), -.001)
            self.assertTrue(abs(mapped.width() - size.width()) < .001 or
                            abs(mapped.height() - size.height()) < .001)
            for dpr in (1, 1.25, 2):
                art.prepare(scale, dpr, cover_art(TRACKS[0].colors, 512, circular=True))
                self.assertGreaterEqual(art.density, scale * dpr)
                # DPR affects resolution only, never on-screen geometry.
                self.assertEqual(art.layout_transform(size), (scale, origin))

    def test_resize_and_dpr_replace_only_current_density_bucket(self):
        art = self.deck._asset_art
        cover = cover_art(TRACKS[0].colors)
        for width, height in ((672, 534), (850, 674), (1028, 824)):
            self.deck.resize(width, height)
            self.assertFalse(self.deck.grab().isNull())
            scale = min(width / 820, height / 650)
            for dpr in (1, 1.25, 2):
                art.prepare(scale, dpr, cover)
                self.assertEqual(art.density, max(1, math.ceil(scale * dpr * 2) / 2))
                self.assertEqual(set(art.buffers), set(LAYER_NAMES))
                for name, buf in art.buffers.items():
                    self.assertEqual(buf.width(), math.ceil(art.rect(name).width() * art.density))
                    self.assertEqual(buf.height(), math.ceil(art.rect(name).height() * art.density))
                keys = [buf.cacheKey() for buf in art.buffers.values()] + [art.label.cacheKey()]
                art.prepare(scale, dpr, cover)
                self.assertEqual(keys, [buf.cacheKey() for buf in art.buffers.values()]
                                 + [art.label.cacheKey()])

    def test_shared_geometry_keeps_label_centered_and_stylus_on_grooves(self):
        art = self.deck._asset_art
        data = art.metadata
        center = QPointF(*data["record_center"])
        vinyl = data["layers"]["vinyl"]
        source_center = vinyl.get("source_center", [n / 2 for n in vinyl["source_size"]])
        for axis in (0, 1):
            mapped = vinyl["rect"][axis] + source_center[axis] * vinyl["rect"][axis + 2] / vinyl["source_size"][axis]
            self.assertAlmostEqual(mapped, data["record_center"][axis])
        self.assertEqual(QRectF(*data["label"]["rect"]).center(), center)
        arm = data["layers"]["tonearm"]
        rect = art.rect("tonearm")
        sx, sy = rect.width() / arm["source_size"][0], rect.height() / arm["source_size"][1]
        self.assertAlmostEqual(sx, sy)
        for source, target in (("source_pivot", "arm_pivot"), ("source_stylus", "stylus")):
            x, y = arm[source]
            self.assertAlmostEqual(rect.x() + x * sx, data[target][0])
            self.assertAlmostEqual(rect.y() + y * sy, data[target][1])
        stylus = QPointF(*data["stylus"]) - center
        distance = math.hypot(stylus.x(), stylus.y())
        self.assertGreater(distance, data["record_radius"] * .7)
        self.assertLess(distance, data["record_radius"] * .95)
        for name in LAYER_NAMES:
            self.assertTrue(QRectF(0, 0, *art.design_size).contains(art.rect(name)))

    def test_rotation_hooks_keep_static_mount_and_base_fixed(self):
        art = self.deck._asset_art
        art.prepare(1, 1, cover_art(TRACKS[0].colors))
        def compose(record=0, arm=0):
            pixmap = QPixmap(820, 650)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            art.paint(painter, record_angle=record, arm_angle=arm)
            painter.end()
            return pixmap.toImage()
        still = compose()
        record_rotated = compose(record=15)
        arm_rotated = compose(arm=-10)
        self.assertNotEqual(still, record_rotated)
        self.assertNotEqual(still, arm_rotated)
        # Separate static mount left of the gimbal and far from the record.
        mount_area = QRectF(676, 100, 12, 20).toRect()
        base_area = QRectF(10, 550, 70, 80).toRect()
        for moved in (record_rotated, arm_rotated):
            self.assertEqual(still.copy(base_area), moved.copy(base_area))
        self.assertEqual(still.copy(mount_area), record_rotated.copy(mount_area))

    def test_cabinet_extension_preserves_deck_and_lower_wood_detail(self):
        art = self.deck._asset_art
        art.prepare(1, 1, cover_art(TRACKS[0].colors))
        def render(extension):
            image = QImage(820, 650 + extension, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            art.paint(painter, transport_extension=extension)
            painter.end()
            return image
        before, after = render(0), render(112)
        # Neither Stay niche, the record, nor the arm is stretched by the
        # new fascia; only the wood band below them gains vertical space.
        self.assertEqual(before.copy(0, 0, 820, 580), after.copy(0, 0, 820, 580))
        self.assertEqual(before.copy(0, 600, 820, 50), after.copy(0, 712, 820, 50))
        self.assertGreater(after.pixelColor(20, 630).alpha(), 245)


if __name__ == "__main__":
    unittest.main()
