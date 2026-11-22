# -*- coding: utf-8 -*-
"""Shared helpers for the Steam-style library pages."""

import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox

from core.runtime_utils import (
    app_prefix_info,
    migrate_prefix,
    prefix_needs_migration,
)

MIME_APP = 'application/x-beer-app'

_PIXMAP_CACHE = {}


def enable_ime(widget):
    """Make sure text widgets accept input method events (Chinese IME)."""
    widget.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
    widget.setInputMethodHints(Qt.InputMethodHint.ImhNone)


def prepare_app_prefix(parent, config, app, translator):
    """Resolve an application's own prefix and offer legacy data migration.

    Returns ``(runtime_type, prefix_path)`` or ``None`` when the user cancels
    the launch.  A ``('', '')`` result means the application is native.
    """
    runtime_type, prefix, legacy = app_prefix_info(config, app)
    if not runtime_type or not prefix:
        return runtime_type, prefix

    already_asked = bool(app.get('legacy_prefix_prompted'))
    if already_asked or not prefix_needs_migration(
        runtime_type, prefix, legacy
    ):
        return runtime_type, prefix

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(translator('prefix_migrate_title'))
    box.setText(translator('prefix_migrate_msg').format(
        path=legacy, name=app.get('name', '')
    ))
    move_button = box.addButton(
        translator('prefix_migrate_move'), QMessageBox.ButtonRole.AcceptRole
    )
    copy_button = box.addButton(
        translator('prefix_migrate_copy'), QMessageBox.ButtonRole.ActionRole
    )
    box.addButton(
        translator('prefix_migrate_skip'), QMessageBox.ButtonRole.RejectRole
    )
    box.exec()

    clicked = box.clickedButton()
    if clicked is None:
        return None

    app['legacy_prefix_prompted'] = True
    mode = ''
    if clicked is move_button:
        mode = 'move'
    elif clicked is copy_button:
        mode = 'copy'

    if mode:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            migrated = migrate_prefix(legacy, prefix, mode)
        finally:
            QApplication.restoreOverrideCursor()
        if not migrated:
            QMessageBox.warning(
                parent, translator('warning'),
                translator('prefix_migrate_failed')
            )

    config._save_apps()
    return runtime_type, prefix


def make_filter_icon(size=18):
    """Draw a three-bar filter icon that works in both themes."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen()
    pen.setColor(Qt.GlobalColor.gray)
    pen.setWidth(2)
    painter.setPen(pen)
    step = size // 4
    for index in range(1, 4):
        y = step * index
        painter.drawLine(3, y, size - 3, y)
    painter.end()
    return QIcon(pixmap)


def resolve_app_pixmap(app, size=64):
    """Return the best available pixmap for a saved application."""
    icon_path = app.get('icon_path', '')
    icon_name = app.get('icon_name', '')
    cache_key = (icon_path, icon_name, size)
    cached = _PIXMAP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if icon_path and os.path.isfile(icon_path):
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            result = _scale(pixmap, size)
            _PIXMAP_CACHE[cache_key] = result
            return result

    if icon_name:
        icon = QIcon.fromTheme(icon_name)
        if not icon.isNull():
            result = _scale(icon.pixmap(size, size), size)
            _PIXMAP_CACHE[cache_key] = result
            return result
        from core.desktop_importer import resolve_icon_path
        resolved = resolve_icon_path(icon_name)
        if resolved:
            pixmap = QPixmap(resolved)
            if not pixmap.isNull():
                result = _scale(pixmap, size)
                _PIXMAP_CACHE[cache_key] = result
                return result

    _PIXMAP_CACHE.pop(cache_key, None)
    return QPixmap()


def _scale(pixmap, size):
    if pixmap.isNull():
        return pixmap
    return pixmap.scaled(
        QSize(size, size),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def fallback_app_pixmap(size=64):
    """Return the beer emoji application icon as a pixmap."""
    from core.app_icon import get_app_icon
    pixmap = get_app_icon().pixmap(size, size)
    return pixmap


def app_runtime_label(app, translator, runtimes=None):
    """Return the runtime display name without the ``Runtime:`` prefix."""
    if app.get('native'):
        return translator('native_linux_app')

    path = app.get('proton_path', '') or ''
    if not path:
        return translator('not_set')

    for runtime in runtimes or []:
        if os.path.realpath(runtime.get('path', '')) == os.path.realpath(path):
            name = runtime.get('name', '')
            version = runtime.get('version_str', '')
            if name and version and version not in name:
                return f'{name} {version}'
            return name or os.path.basename(path)

    return os.path.basename(path) or translator('not_set')


def app_category_keys(app):
    """Return the category keys used by the category filter panel."""
    keys = set()
    if app.get('native'):
        keys.add('native')
    else:
        runtime_type = (app.get('runtime_type') or '').lower()
        if not runtime_type and app.get('proton_path'):
            name = os.path.basename(app.get('proton_path', '')).lower()
            runtime_type = 'proton' if 'proton' in name else 'wine'
        if runtime_type in ('proton', 'wine'):
            keys.add(runtime_type)

    architecture = str(app.get('architecture', 'auto'))
    if architecture == '32':
        keys.add('arch32')
    elif architecture == '64':
        keys.add('arch64')

    for tag in app.get('tags') or []:
        tag = str(tag).strip()
        if tag:
            keys.add(f'tag:{tag}')
    return keys


def format_duration(seconds, translator):
    """Format a duration in seconds using localized units."""
    try:
        total = int(seconds or 0)
    except (TypeError, ValueError):
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    hour_unit = translator('unit_hour')
    minute_unit = translator('unit_minute')
    second_unit = translator('unit_second')
    if hours:
        return f'{hours} {hour_unit} {minutes} {minute_unit}'
    if minutes:
        return f'{minutes} {minute_unit} {secs} {second_unit}'
    return f'{secs} {second_unit}'
