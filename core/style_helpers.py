# -*- coding: utf-8 -*-
"""
Helpers for generating small UI assets (e.g. spinbox/combobox arrows)
that Qt stylesheets can reference via image: url(...).
"""

import os


def _arrow_path(name, theme):
    """Return the path where a themed arrow icon should be stored."""
    arrows_dir = os.path.join(os.path.expanduser('~'), '.config', 'Beer', 'arrows')
    os.makedirs(arrows_dir, exist_ok=True)
    return os.path.join(arrows_dir, f'{name}_{theme}.png')


def ensure_arrow_icons(theme='dark'):
    """Generate small arrow PNGs for QSpinBox/QComboBox buttons.

    Returns a dict mapping arrow names to absolute file paths.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # If Pillow is unavailable, callers should fall back to native arrows.
        return {}

    color = '#aaaaaa' if theme == 'dark' else '#666666'
    size = (16, 16)
    names = {
        'up': [(8, 3), (13, 11), (3, 11)],
        'down': [(8, 13), (13, 5), (3, 5)],
    }

    paths = {}
    for name, points in names.items():
        path = _arrow_path(name, theme)
        if not os.path.exists(path):
            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.polygon(points, fill=color)
            img.save(path)
        paths[name] = path

    return paths
