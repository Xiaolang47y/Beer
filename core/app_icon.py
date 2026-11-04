# -*- coding: utf-8 -*-
"""
Application icon helpers for Beer.

The icon is the beer emoji (🍺).  Qt renders it with a colour emoji font when
one is available.  On systems without an emoji font a small vector beer mug
fallback is drawn so the application always has a usable icon.
"""

import os

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen,
    QPixmap, QBrush
)

_EMOJI = '🍺'
_EMOJI_FONTS = (
    'Noto Color Emoji',
    'Apple Color Emoji',
    'Segoe UI Emoji',
    'EmojiOne Color',
    'Twemoji Mozilla',
    'JoyPixels',
    'Symbola',
)

_ICON_CACHE = None
_ICON_PATH_CACHE = None


def _emoji_font(size):
    families = set(QFontDatabase.families())
    for family in _EMOJI_FONTS:
        if family in families:
            font = QFont(family)
            font.setPixelSize(int(size * 0.74))
            return font
    return None


def _draw_fallback_mug(painter, size):
    """Draw a simple beer mug used when no emoji font is installed."""
    margin = size * 0.14
    body = QRectF(margin, size * 0.30, size * 0.54, size * 0.56)

    # Handle
    handle = QPainterPath()
    handle.addRoundedRect(
        QRectF(size * 0.62, size * 0.42, size * 0.28, size * 0.32),
        size * 0.12, size * 0.12
    )
    painter.setPen(QPen(QColor('#d9a441'), max(2, int(size * 0.035))))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(handle)

    # Glass body
    gradient_top = QColor('#f4b63f')
    gradient_bottom = QColor('#d98613')
    body_path = QPainterPath()
    body_path.addRoundedRect(body, size * 0.05, size * 0.05)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient_top))
    painter.drawPath(body_path)

    # Beer fill (lower part of the glass)
    fill = QRectF(body.left(), body.top() + body.height() * 0.32,
                  body.width(), body.height() * 0.68)
    painter.setBrush(QBrush(gradient_bottom))
    painter.drawRect(fill)

    # Foam
    painter.setBrush(QBrush(QColor('#fff8e1')))
    foam_height = body.height() * 0.34
    painter.drawRoundedRect(
        QRectF(body.left() - size * 0.015, body.top() - foam_height * 0.55,
               body.width() + size * 0.03, foam_height),
        size * 0.1, size * 0.1
    )
    for i in range(3):
        radius = size * (0.10 - i * 0.012)
        painter.drawEllipse(
            QRectF(body.left() + body.width() * (0.12 + i * 0.3) - radius / 2,
                   body.top() - foam_height * 0.60 - radius / 2,
                   radius, radius)
        )


def render_beer_icon(size=256):
    """Render the beer emoji to a transparent QPixmap."""
    size = max(16, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    font = _emoji_font(size)
    if font is not None:
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(
            QRectF(0, 0, size, size),
            int(Qt.AlignmentFlag.AlignCenter),
            _EMOJI
        )
    else:
        _draw_fallback_mug(painter, size)

    painter.end()
    return pixmap


def get_icon_path(size=256):
    """Return a cached PNG path for the beer emoji icon."""
    global _ICON_PATH_CACHE
    if _ICON_PATH_CACHE and os.path.exists(_ICON_PATH_CACHE):
        return _ICON_PATH_CACHE

    icon_dir = os.path.join(os.path.expanduser('~'), '.config', 'Beer')
    os.makedirs(icon_dir, exist_ok=True)
    path = os.path.join(icon_dir, 'beer-emoji.png')

    # Re-render if the requested size changed significantly.
    if not os.path.exists(path):
        pixmap = render_beer_icon(size)
        if not pixmap.save(path, 'PNG'):
            return ''

    _ICON_PATH_CACHE = path
    return path


def get_app_icon():
    """Return the beer emoji as a QIcon."""
    global _ICON_CACHE
    if _ICON_CACHE is not None:
        return _ICON_CACHE

    icon_path = get_icon_path()
    if icon_path and os.path.exists(icon_path):
        _ICON_CACHE = QIcon(icon_path)
    else:
        _ICON_CACHE = QIcon(render_beer_icon())
    return _ICON_CACHE
