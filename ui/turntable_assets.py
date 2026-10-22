"""Image-only turntable composition. Original procedural art remains a fallback.

All placements and pivots live in assets/turntable/metadata.json. Source QImages
are shared (and safe across QApplication lifetimes); each widget retains just
one density bucket of QPixmaps. No file access or image decoding during paint.
"""
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath, QPixmap

ASSET_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "turntable" / "approved"
LAYER_NAMES = ("base", "mount", "vinyl", "spindle", "tonearm")


@dataclass(frozen=True)
class Artwork:
    metadata: dict
    images: dict


def _numbers(value, length, positive=False):
    if (not isinstance(value, list) or len(value) != length
            or any(type(n) not in (int, float) or not math.isfinite(n) for n in value)
            or (positive and any(n <= 0 for n in value))):
        raise ValueError("Invalid coordinate or size")
    return value


@lru_cache(maxsize=4)
def load_artwork(directory=ASSET_DIRECTORY):
    """Return (complete pack, None), or (None, actionable diagnostic).

    Packs are immutable by convention. A missing/corrupt file rejects the whole
    pack, so a photograph can never accidentally mix with procedural pieces.
    Restart the app after installing/replacing assets to reload the cache.
    """
    directory = Path(directory)
    try:
        data = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        if data["version"] != 1:
            raise ValueError("Unsupported artwork version")
        width, height = _numbers(data["design_size"], 2, positive=True)
        bounds = QRectF(0, 0, width, height)
        viewport = QRectF(*_numbers(data.get("viewport", [0, 0, width, height]), 4))
        if viewport.isEmpty() or not bounds.contains(viewport):
            raise ValueError("Invalid artwork viewport")
        split = _numbers([data.get("transport_split", 580)], 1, positive=True)[0]
        if split + 20 >= viewport.bottom():
            raise ValueError("Invalid cabinet split")
        data["transport_split"] = split
        for name in ("record_center", "arm_pivot", "stylus"):
            point = QPointF(*_numbers(data[name], 2))
            if not bounds.contains(point):
                raise ValueError(f"Anchor outside the deck: {name}")
        radius = _numbers([data["record_radius"]], 1, positive=True)[0]
        if radius > min(width, height) / 2:
            raise ValueError("Record radius outside the deck")
        if not QColor(data["background"]).isValid():
            raise ValueError("Invalid background")
        label = QRectF(*_numbers(data["label"]["rect"], 4))
        if label.isEmpty() or not bounds.contains(label):
            raise ValueError("Invalid label bounds")
        paper = QRectF(*_numbers(data["label"]["paper_source"], 4))
        if paper.isEmpty():
            raise ValueError("Invalid paper bounds")
        images = {}
        for name in LAYER_NAMES:
            spec = data["layers"][name]
            filename = spec["file"]
            if not isinstance(filename, str) or Path(filename).name != filename:
                raise ValueError(f"Invalid asset filename: {name}")
            rect = QRectF(*_numbers(spec["rect"], 4))
            if rect.isEmpty() or not bounds.contains(rect):
                raise ValueError(f"Layer outside the deck: {name}")
            expected = _numbers(spec["source_size"], 2, positive=True)
            if "source_center" in spec:
                anchor = QPointF(*_numbers(spec["source_center"], 2))
                if not QRectF(0, 0, *expected).contains(anchor):
                    raise ValueError("Image anchor outside source")
            reader = QImageReader(str(directory / filename))
            if reader.size().toTuple() != tuple(expected):
                raise ValueError(f"Missing, corrupt or unexpected image size: {filename}")
            if name == "vinyl" and not QRectF(0, 0, *expected).contains(paper):
                raise ValueError("Paper source outside vinyl image")
            if "decode_max" in spec:
                limit = _numbers([spec["decode_max"]], 1, positive=True)[0]
                reader.setScaledSize(reader.size().scaled(
                    int(limit), int(limit), Qt.AspectRatioMode.KeepAspectRatio))
            image = reader.read()
            if image.isNull() or not image.hasAlphaChannel():
                raise ValueError(f"Missing RGBA pixels: {filename}")
            # Real transparency, not an opaque PNG with a painted checkerboard.
            if any(image.pixelColor(x, y).alpha() != 0 for x, y in (
                    (0, 0), (image.width() - 1, 0),
                    (0, image.height() - 1), (image.width() - 1, image.height() - 1))):
                raise ValueError(f"Opaque background at corners: {filename}")
            images[name] = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        return Artwork(data, images), None
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        return None, f"Turntable assets unavailable: {exc}"


def cover_source_rect(size):
    """Centered square crop: preserve proportions of future non-square covers."""
    edge = min(size.width(), size.height())
    return QRectF((size.width() - edge) / 2, (size.height() - edge) / 2, edge, edge)


class LayeredTurntable:
    def __init__(self, artwork):
        self.artwork = artwork
        self.metadata = artwork.metadata
        self.density = None
        self.cover_key = None
        self.buffers = {}
        self.label = None

    @property
    def design_size(self):
        return self.metadata["design_size"]

    def rect(self, name):
        return QRectF(*self.metadata["layers"][name]["rect"])

    def layout_transform(self, size, transport_height=0):
        """Fit the useful silhouette, not the transparent export padding."""
        width, height = self.design_size
        viewport = QRectF(*self.metadata.get("viewport", [0, 0, width, height]))
        scale = min(size.width() / viewport.width(),
                    (size.height() - transport_height) / viewport.height())
        # Seat the cabinet against the transport fascia instead of leaving half
        # the aspect-ratio padding between the two parts of the player.
        return scale, QPointF((size.width() - viewport.width() * scale) / 2 - viewport.x() * scale,
                             size.height() - transport_height - viewport.bottom() * scale)

    @staticmethod
    def _draw(painter, rect, pixmap):
        painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))

    def prepare(self, scale, dpr, cover):
        density = max(1, math.ceil(scale * dpr * 2) / 2)
        if self.density != density:
            buffers = {}
            for name in LAYER_NAMES:
                rect = self.rect(name)
                size = QSize(math.ceil(rect.width() * density), math.ceil(rect.height() * density))
                buffers[name] = QPixmap.fromImage(self.artwork.images[name].scaled(
                    size, Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
            self.buffers = buffers
            self.density = density
            self.cover_key = None
        if self.cover_key != cover.cacheKey():
            self.label = self._compose_label(cover)
            self.cover_key = cover.cacheKey()

    def _compose_label(self, cover):
        rect = QRectF(*self.metadata["label"]["rect"])
        label = QPixmap(math.ceil(rect.width() * self.density),
                        math.ceil(rect.height() * self.density))
        label.fill(Qt.GlobalColor.transparent)
        painter = QPainter(label)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                               QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(self.density, self.density)
        target = QRectF(0, 0, rect.width(), rect.height())
        clip = QPainterPath()
        clip.addEllipse(target)
        painter.setClipPath(clip)
        painter.drawPixmap(target, cover, cover_source_rect(cover.size()))
        # Printed-paper shading and embossing come from the generated photograph.
        # Multiply preserves the cover's colors; no square sleeve pasted on top.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        painter.setOpacity(.72)
        painter.drawImage(target, self.artwork.images["vinyl"],
                          QRectF(*self.metadata["label"]["paper_source"]))
        painter.setOpacity(1)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(223, 189, 141, 95))
        painter.drawEllipse(target.adjusted(.65, .65, -.65, -.65))
        painter.end()
        return label

    def paint(self, painter, record_angle=0, arm_angle=0, transport_extension=0):
        """Angles are composition hooks only: no timers or animation states."""
        if transport_extension:
            # Vertical three-slice composition extends only the wooden fascia.
            # Top, corners and bottom retain their original texture/scale;
            # no second enclosure is drawn around the already framed deck.
            rect, base = self.rect("base"), self.buffers["base"]
            split = self.metadata["transport_split"]
            sy = base.height() / rect.height()
            band = 20
            for target, source in (
                (QRectF(0, 0, rect.width(), split), QRectF(0, 0, base.width(), split * sy)),
                (QRectF(0, split, rect.width(), band + transport_extension),
                 QRectF(0, split * sy, base.width(), band * sy)),
                (QRectF(0, split + band + transport_extension, rect.width(), rect.height() - split - band),
                 QRectF(0, (split + band) * sy, base.width(), base.height() - (split + band) * sy)),
            ):
                painter.drawPixmap(target, base, source)
        else:
            self._draw(painter, self.rect("base"), self.buffers["base"])
        self._draw(painter, self.rect("mount"), self.buffers["mount"])
        center = QPointF(*self.metadata["record_center"])
        painter.save()
        painter.translate(center)
        painter.rotate(record_angle)
        painter.translate(-center)
        self._draw(painter, self.rect("vinyl"), self.buffers["vinyl"])
        self._draw(painter, QRectF(*self.metadata["label"]["rect"]), self.label)
        painter.restore()
        # These do not rotate with the record. The foot is also independent of
        # the arm's moving brass gimbal, counterweight, tube and cartridge.
        self._draw(painter, self.rect("spindle"), self.buffers["spindle"])
        pivot = QPointF(*self.metadata["arm_pivot"])
        painter.save()
        painter.translate(pivot)
        painter.rotate(arm_angle)
        painter.translate(-pivot)
        self._draw(painter, self.rect("tonearm"), self.buffers["tonearm"])
        painter.restore()
