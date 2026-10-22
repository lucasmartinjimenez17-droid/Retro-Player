"""Local QPainter materials and independent, static turntable layers.

Coordinates stay in the original 820 × 650 design space. Rasterization density
is supplied by the widget (layout scale × screen DPR); no animation or I/O here.
"""
import math
import random
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient,
)

CENTER = QPointF(363, 319)
ARM_BOUNDS = QRectF(532, 15, 268, 468)


def raster(width, height, density, draw):
    """Physical pixel buffer, composited later into an explicit logical rect."""
    pixmap = QPixmap(math.ceil(width * density), math.ceil(height * density))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                           QPainter.RenderHint.SmoothPixmapTransform)
    painter.scale(density, density)
    draw(painter)
    painter.end()
    return pixmap


def linear(x1, y1, x2, y2, stops):
    gradient = QLinearGradient(x1, y1, x2, y2)
    for position, color in stops:
        gradient.setColorAt(position, QColor(color))
    return gradient


def ellipse(p, center, radius, brush, pen=Qt.PenStyle.NoPen):
    p.setPen(pen)
    p.setBrush(brush)
    p.drawEllipse(center, radius, radius)


def shadow(p, center, radius, spread=12, opacity=110):
    gradient = QRadialGradient(center, radius + spread)
    gradient.setColorAt(0, QColor(0, 0, 0, opacity))
    gradient.setColorAt(radius / (radius + spread), QColor(0, 0, 0, opacity))
    gradient.setColorAt(1, QColor(0, 0, 0, 0))
    ellipse(p, center, radius + spread, gradient)


@lru_cache(maxsize=1)
def deck_texture():
    """Subtle satin grain, reproducible and generated once (CPU cache only)."""
    rng = random.Random(17)
    def draw(p):
        p.fillRect(QRectF(0, 0, 192, 192), QColor("#182733"))
        for _ in range(14500):
            p.setPen(QColor(120, 142, 155, rng.randrange(4, 17)) if rng.random() > .5
                     else QColor(0, 6, 12, rng.randrange(5, 22)))
            p.drawPoint(QPointF(rng.random() * 192, rng.random() * 192))
    return raster(192, 192, 1, draw)


@lru_cache(maxsize=1)
def wood_texture():
    """Long walnut fibres, with nonperiodic spacing and soft tonal variation."""
    rng = random.Random(81)
    def draw(p):
        p.fillRect(QRectF(0, 0, 1024, 512), linear(0, 0, 0, 512, (
            (0, "#735037"), (.35, "#65422e"), (.72, "#795139"), (1, "#543725"))))
        y = -12.0
        while y < 528:
            y += rng.uniform(.7, 2.8)
            drift, bend = rng.uniform(-9, 9), rng.uniform(-18, 18)
            path = QPainterPath(QPointF(-2, y))
            path.cubicTo(260, y + bend, 440, y - bend * .6, 655, y + drift)
            path.cubicTo(800, y + drift + bend * .5, 930, y + drift, 1026, y + drift * .4)
            p.setPen(QPen(QColor(25, 11, 5, rng.randrange(12, 55)) if rng.random() < .65
                          else QColor(214, 165, 108, rng.randrange(8, 28)), rng.uniform(.3, 1.2)))
            p.drawPath(path)
        for _ in range(11000):
            p.setPen(QColor(236, 196, 142, rng.randrange(3, 13)))
            p.drawPoint(QPointF(rng.random() * 1024, rng.random() * 512))
    return raster(1024, 512, 1, draw).toImage()


def paint_wood(p, width, height):
    rect = QRectF(1, 1, width - 2, height - 2)
    clip = QPainterPath()
    clip.addRoundedRect(rect, 23, 23)
    p.setClipPath(clip)
    p.drawImage(rect, wood_texture(), QRectF(wood_texture().rect()))
    p.fillRect(rect, linear(0, 0, width, height, (
        (0, QColor(255, 218, 164, 74)), (.3, QColor(255, 211, 155, 12)),
        (.75, QColor(0, 0, 0, 12)), (1, QColor(0, 0, 0, 95)))))
    # Rounded joinery: lit upper bevel, dark vertical fascia and inner seam.
    p.setBrush(Qt.BrushStyle.NoBrush)
    for inset, alpha in ((2, 105), (3, 55), (5, 28)):
        p.setPen(QPen(QColor(244, 202, 149, alpha), 1))
        p.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), 23 - inset, 23 - inset)
    p.fillRect(QRectF(0, height - 14, width, 14), linear(0, height - 14, 0, height, (
        (0, QColor(0, 0, 0, 0)), (.15, QColor(0, 0, 0, 20)), (1, QColor(0, 0, 0, 125)))))
    p.setPen(QPen(QColor("#39271d"), 1.5))
    p.drawRoundedRect(rect, 23, 23)
    p.setPen(QPen(linear(0, 0, width, height, (
        (0, "#bc9166"), (.45, "#795239"), (1, "#2a1c14"))), 3))
    p.drawRoundedRect(rect.adjusted(7, 7, -7, -7), 17, 17)
    p.setClipping(False)


def paint_surface(p, width, height):
    rect = QRectF(1, 1, width - 2, height - 2)
    clip = QPainterPath()
    clip.addRoundedRect(rect, 18, 18)
    p.setClipPath(clip)
    # Continue the wooden bevel into the drawing, without changing any layout.
    p.drawImage(rect, wood_texture(), QRectF(wood_texture().rect()))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(linear(0, 0, width, height, (
        (0, "#b88d60"), (.4, "#886040"), (1, "#35251b"))), 2))
    p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 17, 17)
    rect = rect.adjusted(6, 6, -6, -6)
    clip = QPainterPath()
    clip.addRoundedRect(rect, 13, 13)
    p.setClipPath(clip)
    p.drawTiledPixmap(rect, deck_texture())
    lighting = QRadialGradient(QPointF(width * .2, height * .12), width * .95)
    lighting.setColorAt(0, QColor(113, 134, 150, 24))
    lighting.setColorAt(.6, QColor(4, 10, 16, 8))
    lighting.setColorAt(1, QColor(0, 4, 9, 100))
    p.fillRect(rect, lighting)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for inset, color in ((0, "#080c10"), (1, "#080e14"), (2.5, "#101c26"), (4, "#3b4750")):
        p.setPen(QPen(QColor(color), 1.2))
        p.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), 13 - inset, 13 - inset)
    p.setClipping(False)


def brushed_metal(p, center, radius):
    finish = QConicalGradient(center, 30)
    for stop, color in ((0, "#806345"), (.13, "#ddc49a"), (.3, "#997c55"),
                        (.48, "#685036"), (.62, "#c6ae85"), (.8, "#a38b66"), (1, "#806345")):
        finish.setColorAt(stop, QColor(color))
    ellipse(p, center, radius, finish, QPen(QColor("#d1b58a"), .65))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for r in range(2, int(radius), 2):
        p.setPen(QPen(QColor(255, 234, 195, 18), .35))
        p.drawEllipse(center, r, r)


def screw(p, x, y, radius=2.6):
    ellipse(p, QPointF(x + .5, y + 1), radius + .8, QColor("#090e11"))
    ellipse(p, QPointF(x, y), radius, linear(x - radius, y - radius, x + radius, y + radius,
            ((0, "#ddc49c"), (.45, "#9c825e"), (1, "#4a3927"))))
    p.setPen(QPen(QColor("#3d3226"), .8))
    p.drawLine(QPointF(x - radius * .55, y + .6), QPointF(x + radius * .55, y - .6))


def paint_base(p):
    shadow(p, CENTER + QPointF(4, 11), 306, 12, 185)
    # Platter beneath the record: a warm, machined rim with a dark underside.
    ellipse(p, CENTER + QPointF(0, 6), 311, linear(0, 315, 0, 636, (
        (0, "#191d1f"), (.8, "#292d2b"), (.96, "#686152"), (1, "#222523"))))
    for offset, color in ((5, "#8b806a"), (3.5, "#303633")):
        ellipse(p, CENTER + QPointF(0, offset), 310.5, Qt.BrushStyle.NoBrush,
                QPen(QColor(color), .8))
    rim = QConicalGradient(CENTER, 38)
    for stop, color in ((0, "#8b806d"), (.16, "#beb6a4"), (.27, "#6e6c60"),
                        (.5, "#292f30"), (.64, "#9b9686"), (.8, "#4c514c"), (1, "#9c8e78")):
        rim.setColorAt(stop, QColor(color))
    ellipse(p, CENTER, 310, rim, QPen(QColor("#726957"), 1))
    for radius in (306.5, 308.7):
        ellipse(p, CENTER, radius, Qt.BrushStyle.NoBrush, QPen(QColor(229, 217, 189, 75), .6))
    ellipse(p, CENTER + QPointF(0, 2.5), 304, QColor("#020406"))
    ellipse(p, CENTER, 302, QColor("#0b1115"), QPen(QColor("#4e575b"), .6))
    # Speed selector: rubber mounting, vertical metal wall and brushed cap.
    knob = QPointF(55, 68)
    shadow(p, knob + QPointF(3, 6), 25, 10, 140)
    ellipse(p, knob + QPointF(0, 4), 28, QColor("#090f14"), QPen(QColor("#4c5050"), .7))
    ellipse(p, knob + QPointF(0, 3), 22, QColor("#5b442b"))
    brushed_metal(p, knob, 21)
    p.setPen(QPen(QColor("#433321"), 1.2))
    p.drawLine(QPointF(55, 49), QPointF(55, 56))
    p.setPen(QColor("#baa88b"))
    small = QFont("Segoe UI")
    small.setPixelSize(9)
    p.setFont(small)
    p.drawText(QRectF(25, 108, 70, 16), "33     ·     45")
    for angle in (-135, -90, -45):
        a = math.radians(angle)
        ellipse(p, knob + QPointF(math.cos(a) * 33, math.sin(a) * 33), .8, QColor("#bfa67e"))
    # The pivot footing remains attached to the deck when the arm is rotated.
    pivot = QPointF(728, 105)
    shadow(p, pivot + QPointF(4, 7), 49, 11, 150)
    ellipse(p, pivot + QPointF(0, 3), 51, QColor("#090f15"))
    ellipse(p, pivot, 50, linear(680, 60, 770, 150, ((0, "#4b555c"), (.45, "#23303a"), (1, "#101c25"))),
            QPen(QColor("#617079"), .7))
    ellipse(p, pivot, 39, QColor("#0b141b"), QPen(QColor("#84755d"), 1))
    ellipse(p, pivot + QPointF(0, 4), 35, QColor("#080e13"), QPen(QColor("#131d25"), 2))
    for x, y in ((696, 80), (765, 90), (716, 144)):
        screw(p, x, y)
    # Restrained engraved branding.
    lettering = QFont("Georgia")
    lettering.setPixelSize(11)
    p.setFont(lettering)
    p.setPen(QColor("#c5ad86"))
    p.drawText(QRectF(24, 578, 220, 22), "R E T R O  P L A Y E R")
    small.setPixelSize(8)
    p.setFont(small)
    p.setPen(QColor("#87949b"))
    p.drawText(QRectF(24, 602, 210, 30), "M U S I C  S O U N D S  B E T T E R\nO N  V I N Y L")
    shadow(p, QPointF(779, 612), 18, 4, 130)
    ellipse(p, QPointF(778, 610), 18, QColor("#101a22"), QPen(QColor("#7d705b"), 1))
    ellipse(p, QPointF(778, 610), 15.5, QColor("#0d171f"), QPen(QColor("#2b3439"), 1))


def paint_record(p):
    center = QPointF(303, 303)
    ellipse(p, center + QPointF(0, 1.8), 301, QColor("#040608"))
    surface = QConicalGradient(center, 24)
    for stop, color in ((0, "#090c0f"), (.075, "#1b2228"), (.14, "#4a5259"),
                        (.185, "#343c43"), (.26, "#0c1013"), (.4, "#080a0d"),
                        (.54, "#12171c"), (.63, "#38434c"), (.69, "#242e36"),
                        (.78, "#0b0f12"), (.93, "#070a0d"), (1, "#090c0f")):
        surface.setColorAt(stop, QColor(color))
    ellipse(p, center, 300, surface)
    # Broad softbox reflection over the radial sheen, under the grooves.
    reflection = QRadialGradient(QPointF(166, 124), 330)
    reflection.setColorAt(0, QColor(206, 219, 227, 26))
    reflection.setColorAt(.55, QColor(188, 207, 222, 9))
    reflection.setColorAt(1, QColor(188, 207, 222, 0))
    ellipse(p, center, 298, reflection)
    rng = random.Random(221)
    radius = 115.0
    p.setBrush(Qt.BrushStyle.NoBrush)
    while radius < 298:
        radius += rng.uniform(.55, 1.08)
        groove = QConicalGradient(center, 24)
        alpha = rng.randrange(18, 53)
        for stop, strength in ((0, .2), (.13, 1), (.21, .6), (.35, .08),
                               (.54, .15), (.64, .8), (.76, .1), (1, .2)):
            groove.setColorAt(stop, QColor(192, 202, 209, int(alpha * strength)))
        p.setPen(QPen(groove, rng.uniform(.25, .55)))
        p.drawEllipse(center, radius, radius)
    # Quiet separation bands, not regularly spaced or high-contrast rings.
    for radius, width in ((149, 1.4), (192, 1.8), (238, 1.3), (279, 1.6)):
        p.setPen(QPen(QColor(0, 0, 0, 70), width))
        p.drawEllipse(center, radius, radius)
        p.setPen(QPen(QColor(185, 193, 200, 18), .4))
        p.drawEllipse(center, radius + width, radius + width)
    # Fine lead-in, rolled lip and asymmetric edge reflection.
    for radius, color in ((296.8, "#151e25"), (298.3, "#626b70"), (299.2, "#20282d"), (300, "#05080a")):
        p.setPen(QPen(QColor(color), .6))
        p.drawEllipse(center, radius, radius)
    p.setPen(QPen(QColor(199, 203, 200, 90), .85))
    p.drawArc(QRectF(4, 4, 598, 598), 35 * 16, 108 * 16)
    ellipse(p, center, 114, QColor("#101316"), QPen(QColor("#2c3032"), .6))
    for radius in (111.5, 116, 118.3):
        ellipse(p, center, radius, Qt.BrushStyle.NoBrush, QPen(QColor(153, 162, 163, 40), .45))


def paint_label(p, colors, artwork):
    center = QPointF(112, 112)
    ellipse(p, center + QPointF(0, 1.5), 110.5, QColor("#030507"))
    paper = QColor(colors[0])
    ellipse(p, center, 109, paper, QPen(paper.lighter(145), .8))
    clip = QPainterPath()
    clip.addEllipse(center, 108.5, 108.5)
    p.save()
    p.setClipPath(clip)
    lighting = QLinearGradient(25, 10, 195, 220)
    lighting.setColorAt(0, QColor(243, 214, 171, 22))
    lighting.setColorAt(.5, QColor(0, 0, 0, 0))
    lighting.setColorAt(1, QColor(0, 0, 0, 40))
    p.fillRect(QRectF(0, 0, 224, 224), lighting)
    rng = random.Random(56)
    for _ in range(6000):
        p.setPen(QColor(244, 225, 196, rng.randrange(3, 12)))
        p.drawPoint(QPointF(rng.random() * 224, rng.random() * 224))
    p.setPen(QPen(QColor(242, 220, 185, 65), .5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(center, 103, 103)
    p.drawPixmap(QRectF(49, 49, 126, 126), artwork, QRectF(artwork.rect()))
    p.setPen(QPen(QColor(232, 208, 170, 135), 1))
    p.drawRect(QRectF(48, 48, 128, 128))
    p.setPen(QColor(245, 221, 190, 140))
    lettering = QFont("Segoe UI")
    lettering.setPixelSize(6)
    p.setFont(lettering)
    p.drawText(QRectF(55, 25, 114, 12), Qt.AlignmentFlag.AlignCenter, "STEREO     •     LONG PLAY     •     33⅓")
    p.drawText(QRectF(55, 188, 114, 12), Qt.AlignmentFlag.AlignCenter, "RETRO PLAYER     /     SIDE A")
    p.restore()
    # Pressed hub and spindle are separate from the printed artwork.
    ellipse(p, center, 17, Qt.BrushStyle.NoBrush, QPen(QColor(0, 0, 0, 26), 1))
    ellipse(p, center, 14.5, Qt.BrushStyle.NoBrush, QPen(QColor(245, 221, 194, 22), .6))


def paint_spindle(p):
    shadow(p, CENTER + QPointF(3, 4), 7, 6, 140)
    ellipse(p, CENTER, 8, linear(CENTER.x() - 8, CENTER.y() - 8, CENTER.x() + 8, CENTER.y() + 8,
            ((0, "#ddceb2"), (.3, "#94836b"), (.7, "#3a3832"), (1, "#b5a386"))),
            QPen(QColor("#4f4738"), .6))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(linear(CENTER.x() - 4.5, 0, CENTER.x() + 4.5, 0,
               ((0, "#554e40"), (.3, "#f1ead9"), (.55, "#b7b09e"), (1, "#555346"))))
    p.drawRoundedRect(QRectF(CENTER.x() - 4.5, CENTER.y() - 6, 9, 9), 2, 2)
    shine = QRadialGradient(CENTER + QPointF(-2, -5), 7)
    shine.setColorAt(0, QColor("#f3e7cf"))
    shine.setColorAt(.28, QColor("#c3b08a"))
    shine.setColorAt(.65, QColor("#816947"))
    shine.setColorAt(1, QColor("#32291d"))
    p.setBrush(shine)
    p.setPen(QPen(QColor("#c9bfa9"), .5))
    p.drawEllipse(QRectF(CENTER.x() - 4.5, CENTER.y() - 8, 9, 6))


def arm_path():
    path = QPainterPath(QPointF(721, 130))
    path.lineTo(687, 302)
    path.cubicTo(680, 343, 657, 367, 601, 405)
    return path


def paint_tube(p, path):
    """Shaded ribbons follow the tube's normals, including its bend."""
    points, normals = [], []
    for i in range(101):
        t = i / 100
        a, b = path.pointAtPercent(max(0, t - .001)), path.pointAtPercent(min(1, t + .001))
        dx, dy = b.x() - a.x(), b.y() - a.y()
        length = math.hypot(dx, dy)
        points.append(path.pointAtPercent(t))
        normals.append(QPointF(-dy / length, dx / length))
    shades = ("#302c25", "#66533b", "#9e8056", "#c9ad82", "#eee1c5", "#fff2d7",
              "#d4bc91", "#a98b60", "#7c623f", "#665239", "#a28d6b", "#423a2c")
    p.setPen(Qt.PenStyle.NoPen)
    for band, shade in enumerate(shades):
        left, right = -7 + band * 14 / len(shades), -7 + (band + 1) * 14 / len(shades) + .6
        ribbon = QPainterPath(points[0] + normals[0] * left)
        for point, normal in zip(points[1:], normals[1:]):
            ribbon.lineTo(point + normal * left)
        for point, normal in reversed(list(zip(points, normals))):
            ribbon.lineTo(point + normal * right)
        ribbon.closeSubpath()
        p.setBrush(linear(710, 130, 590, 415, (
            (0, QColor(shade).darker(112)), (.2, QColor(shade).lighter(108)),
            (.45, QColor(shade).darker(112)), (.7, QColor(shade).lighter(110)),
            (1, QColor(shade).darker(125)))))
        p.drawPath(ribbon)


def paint_arm(p):
    p.translate(-ARM_BOUNDS.x(), -ARM_BOUNDS.y())
    pivot = QPointF(728, 105)
    path = arm_path()
    p.save()
    p.translate(7, 10)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for width, alpha in ((31, 9), (25, 17), (20, 28), (16, 58)):
        p.setPen(QPen(QColor(0, 0, 0, alpha), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(path)
    p.restore()
    # Rear shaft and cylindrical counterweight, lit from upper left.
    p.save()
    p.translate(737, 54)
    p.rotate(12)
    p.setPen(QPen(QColor("#33291e"), 1))
    p.setBrush(linear(-7, 0, 7, 0, ((0, "#665139"), (.35, "#d4bd94"), (1, "#55412c"))))
    p.drawRect(QRectF(-7, -31, 14, 88))
    p.setBrush(linear(-22, 0, 22, 0, ((0, "#483623"), (.18, "#9c7c52"), (.38, "#e1c9a0"),
                    (.52, "#c6a879"), (.8, "#9a784a"), (1, "#4e3b28"))))
    p.drawRoundedRect(QRectF(-22, -21, 44, 49), 6, 6)
    p.setBrush(QColor("#5e482f"))
    p.drawEllipse(QRectF(-22, 20, 44, 12))
    p.setBrush(linear(-22, -25, 22, -17, ((0, "#b9a17b"), (.5, "#dfcaa6"), (1, "#8f7350"))))
    p.drawEllipse(QRectF(-22, -25, 44, 12))
    p.setPen(QPen(QColor(239, 215, 177, 35), .45))
    for x in range(-18, 20, 3):
        p.drawLine(QPointF(x, -15), QPointF(x, 21))
    p.restore()
    ellipse(p, pivot + QPointF(0, 6), 33, QColor("#211e19"), QPen(QColor("#826d4b"), .7))
    ellipse(p, pivot + QPointF(0, 2), 31, linear(697, 85, 759, 121,
            ((0, "#d4bb90"), (.3, "#736043"), (.7, "#3a3226"), (1, "#b49b70"))))
    brushed_metal(p, pivot + QPointF(0, -3), 27)
    ellipse(p, pivot + QPointF(0, -3), 24.5, Qt.BrushStyle.NoBrush, QPen(QColor(246, 220, 177, 100), .7))
    for x in (696, 760):
        screw(p, x, 109, 4)
    paint_tube(p, path)
    # Socket collars join the tube to the pivot and headshell.
    for x, y, angle in ((720, 135, 11), (605, 402, 53)):
        p.save()
        p.translate(x, y)
        p.rotate(angle)
        p.setPen(QPen(QColor("#4a3927"), .7))
        p.setBrush(linear(-9, 0, 9, 0, ((0, "#705431"), (.32, "#e1c59a"), (.65, "#b49363"), (1, "#4e3b27"))))
        p.drawRoundedRect(QRectF(-9, -7, 18, 14), 2, 2)
        for y in (2.5, 5):
            p.drawLine(QPointF(-9, y), QPointF(9, y))
        p.restore()
    p.save()
    p.translate(598, 406)
    p.rotate(46)
    shadow(p, QPointF(5, 36), 27, 8, 130)
    shell = QPainterPath(QPointF(-14, -9))
    for x, y in ((14, -9), (19, 2), (18, 42), (10, 53), (-11, 53), (-18, 42), (-18, 1)):
        shell.lineTo(x, y)
    shell.closeSubpath()
    p.setPen(QPen(QColor("#11191d"), 1))
    p.setBrush(QColor("#11181b"))
    p.save()
    p.translate(2, 4)
    p.drawPath(shell)
    p.restore()
    p.setBrush(linear(-18, 0, 18, 50, ((0, "#7d8587"), (.18, "#424d53"), (.65, "#232d34"), (1, "#121c22"))))
    p.setPen(QPen(QColor("#9ba3a1"), .8))
    p.drawPath(shell)
    # Separate finger lift and shaped upper shell, rather than a flat tile.
    p.setPen(QPen(QColor("#b9ab90"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    lift = QPainterPath(QPointF(18, 26))
    lift.cubicTo(30, 26, 28, 35, 31, 36)
    p.drawPath(lift)
    # Recessed vents, fasteners, and a small cartridge under the shell.
    for x in (-9, -3, 3, 9):
        p.setPen(QPen(QColor("#121a1e"), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x, 17), QPointF(x, 29))
    for y in (5, 39):
        screw(p, 0, y, 3)
    p.setBrush(linear(-13, 50, 13, 65, ((0, "#e0d1b5"), (.4, "#b09b77"), (1, "#5d4d36"))))
    p.setPen(QPen(QColor("#413426"), .7))
    p.drawRoundedRect(QRectF(-13, 50, 26, 14), 2, 2)
    p.setBrush(QColor("#1a252c"))
    p.drawRoundedRect(QRectF(-9, 60, 18, 5), 1, 1)
    p.setPen(QPen(QColor("#d8d2bd"), 1.2))
    p.drawLine(QPointF(0, 64), QPointF(-1, 70))
    ellipse(p, QPointF(-1, 70), 1, QColor("#eee7cf"))
    p.restore()


def paint_power(p, playing):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#ccb28a" if playing else "#6b6d65"), 1.3))
    p.drawArc(QRectF(771, 603, 14, 14), 135 * 16, 270 * 16)
    p.drawLine(QPointF(778, 601), QPointF(778, 608))
