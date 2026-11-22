# -*- coding: utf-8 -*-
"""Steam-style application detail page."""

import datetime
import os
import shlex

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPixmap,
)
from PyQt6.QtWidgets import (
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from core.runtime_utils import detect_runtime
from ui.dialogs.more_options_dialog import MoreOptionsDialog
from ui.pages.app_helpers import (
    enable_ime, fallback_app_pixmap, resolve_app_pixmap,
)
from ui.widgets import BeerComboBox

NATIVE_DATA = '__native__'


class HeroPanel(QWidget):
    """Custom hero image with a draggable, zoomable logo group."""

    changed = pyqtSignal()
    edit_mode_changed = pyqtSignal(bool)

    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page
        self.app = None
        self.edit_mode = None
        self._pixmap = QPixmap()
        self._logo_pixmap = QPixmap()
        self._logo_rect = QRect()
        self._dragging = None
        self._last_pos = None
        self._moved = False
        self.setMinimumHeight(220)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

        self.btn_confirm = QPushButton(
            page.translator('confirm_position'), self
        )
        self.btn_confirm.setStyleSheet(
            'background-color: #2e7d32; color: white; font-weight: bold;'
            ' border-radius: 4px; padding: 4px 16px;'
        )
        self.btn_confirm.clicked.connect(self.confirm_edit)
        self.btn_confirm.hide()

    # ------------------------------------------------------------------
    def set_app(self, app):
        self.app = app
        self._load_pixmaps()
        self.set_edit_mode(None)
        self.update()

    def set_edit_mode(self, mode):
        """Enter or leave position/zoom editing for ``hero`` or ``logo``."""
        if mode not in ('hero', 'logo'):
            mode = None
        changed = mode != self.edit_mode
        self.edit_mode = mode
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if mode else Qt.CursorShape.ArrowCursor
        )
        self.btn_confirm.setVisible(mode is not None)
        if mode is not None:
            self._position_confirm_button()
        self.update()
        if changed:
            self.edit_mode_changed.emit(mode is not None)

    def _position_confirm_button(self):
        self.btn_confirm.adjustSize()
        self.btn_confirm.move(
            max(8, self.width() - self.btn_confirm.width() - 16), 12
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_confirm_button()

    def _load_pixmaps(self):
        self._pixmap = QPixmap()
        self._logo_pixmap = QPixmap()
        if not self.app:
            return
        hero = self.app.get('hero_image', '')
        if hero and os.path.isfile(hero):
            pixmap = QPixmap(hero)
            if not pixmap.isNull():
                self._pixmap = pixmap
        logo = self.app.get('logo_image', '')
        if logo and os.path.isfile(logo):
            pixmap = QPixmap(logo)
            if not pixmap.isNull():
                self._logo_pixmap = pixmap

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        if not self._pixmap.isNull():
            self._draw_cover(painter, rect)
        else:
            gradient = QLinearGradient(0, 0, 0, rect.height())
            gradient.setColorAt(0.0, QColor(30, 42, 58))
            gradient.setColorAt(1.0, QColor(15, 20, 28))
            painter.fillRect(rect, gradient)
            painter.setPen(QColor(160, 170, 185))
            painter.drawText(
                rect, Qt.AlignmentFlag.AlignCenter,
                self.page.translator('hero_placeholder')
            )

        # Bottom shadow so the logo stays readable on bright images.
        shadow = QLinearGradient(0, rect.height() * 0.55, 0, rect.height())
        shadow.setColorAt(0.0, QColor(0, 0, 0, 0))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 190))
        painter.fillRect(rect, shadow)

        self._draw_logo(painter)
        self._draw_hint(painter)

    def _draw_cover(self, painter, rect):
        scale = float(self.app.get('hero_scale', 1.0) or 1.0)
        offset = self.app.get('hero_offset') or [0, 0]
        image_w = self._pixmap.width()
        image_h = self._pixmap.height()
        if not image_w or not image_h:
            return
        base = max(rect.width() / image_w, rect.height() / image_h)
        factor = base * max(1.0, scale)
        width = image_w * factor
        height = image_h * factor
        x = (rect.width() - width) / 2 + offset[0]
        y = (rect.height() - height) / 2 + offset[1]
        painter.drawPixmap(
            QRect(int(x), int(y), int(width), int(height)), self._pixmap
        )

    def _draw_logo(self, painter):
        if not self.app:
            self._logo_rect = QRect()
            return
        scale = float(self.app.get('logo_scale', 1.0) or 1.0)
        scale = max(0.4, min(3.0, scale))
        hidden = bool(self.app.get('logo_hidden'))
        icon_size = 0 if hidden else int(76 * scale)
        gap = 0 if hidden else 16
        font = QFont()
        font.setBold(True)
        font.setPointSizeF(max(10.0, 20.0 * scale))
        metrics = QFontMetrics(font)
        name = self.app.get('name', '')
        text_width = metrics.horizontalAdvance(name)
        text_height = metrics.height()

        group_width = icon_size + gap + text_width
        group_height = max(icon_size, text_height)
        offset = self.app.get('logo_offset') or [0, 0]
        default_x = 36
        default_y = self.height() - 30 - group_height
        x = int(default_x + offset[0])
        y = int(default_y + offset[1])
        self._logo_rect = QRect(x, y, int(group_width), int(group_height))

        if not hidden:
            pixmap = self._logo_pixmap
            if pixmap.isNull():
                pixmap = resolve_app_pixmap(self.app, icon_size)
            if pixmap.isNull():
                pixmap = fallback_app_pixmap(icon_size)

            icon_rect = QRect(x, y + (group_height - icon_size) // 2,
                              icon_size, icon_size)
            if not pixmap.isNull():
                painter.drawPixmap(icon_rect, pixmap)
            else:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(font)
                painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, '🍺')

        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0, 160))
        text_rect = QRect(
            x + icon_size + gap, y + (group_height - text_height) // 2,
            text_width + 2, text_height,
        )
        painter.drawText(text_rect.translated(2, 2),
                         Qt.AlignmentFlag.AlignVCenter, name)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, name)

    def _draw_hint(self, painter):
        if not self.edit_mode:
            return
        painter.setFont(QFont())
        painter.setPen(QColor(255, 255, 255, 190))
        hint = self.page.translator(
            'hero_hint' if self.edit_mode == 'hero' else 'logo_hint'
        )
        margin = 12
        metrics = QFontMetrics(painter.font())
        width = metrics.horizontalAdvance(hint) + 12
        hint_rect = QRect(
            self.width() - width - margin, self.height() - 26,
            width, 20,
        )
        painter.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            hint,
        )

    # ------------------------------------------------------------------
    # Mouse interactions
    # ------------------------------------------------------------------
    def _in_logo(self, pos):
        return self._logo_rect.contains(pos)

    def mousePressEvent(self, event):
        if not self.app or self.edit_mode is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            target = 'logo' if self._in_logo(event.pos()) else 'hero'
            if target != self.edit_mode:
                return
            self._dragging = target
            self._last_pos = event.pos()
            self._moved = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self.app or self._dragging is None:
            return
        delta = event.pos() - self._last_pos
        self._last_pos = event.pos()
        if delta.isNull():
            return
        self._moved = True
        if self._dragging == 'logo':
            offset = list(self.app.get('logo_offset') or [0, 0])
            offset[0] += delta.x()
            offset[1] += delta.y()
            self.app['logo_offset'] = offset
        else:
            offset = list(self.app.get('hero_offset') or [0, 0])
            offset[0] += delta.x()
            offset[1] += delta.y()
            self.app['hero_offset'] = offset
        self.update()

    def mouseReleaseEvent(self, event):
        if self._dragging is not None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self._moved and self.app:
                key = 'logo_offset' if self._dragging == 'logo' else 'hero_offset'
                self.page.update_app_field(
                    self.app, key, self.app.get(key), refresh=False
                )
        self._dragging = None
        self._last_pos = None

    def wheelEvent(self, event):
        if not self.app or self.edit_mode is None:
            event.ignore()
            return
        step = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        target = 'logo' if self._in_logo(event.position().toPoint()) else 'hero'
        if target != self.edit_mode:
            event.ignore()
            return
        if target == 'logo':
            scale = float(self.app.get('logo_scale', 1.0) or 1.0) * step
            scale = max(0.4, min(3.0, scale))
            self.app['logo_scale'] = scale
            key = 'logo_scale'
        else:
            scale = float(self.app.get('hero_scale', 1.0) or 1.0) * step
            scale = max(1.0, min(4.0, scale))
            self.app['hero_scale'] = scale
            key = 'hero_scale'
        self.update()
        self.page.update_app_field(self.app, key, scale, refresh=False)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------
    def contextMenuEvent(self, event):
        if not self.app:
            return
        menu = QMenu(self)
        if self._in_logo(event.pos()):
            menu.addAction(
                self.page.translator('logo_change'),
                self._choose_logo,
            )
            menu.addAction(
                self.page.translator('logo_edit_position'),
                lambda: self.set_edit_mode('logo'),
            )
            menu.addAction(
                self.page.translator('logo_use_app_icon'),
                self._use_app_icon,
            )
            menu.addAction(
                self.page.translator('logo_no_icon'),
                self._no_logo_icon,
            )
            menu.addAction(
                self.page.translator('logo_reset'),
                self._reset_logo,
            )
        else:
            menu.addAction(
                self.page.translator('hero_change_image'),
                self._choose_hero,
            )
            menu.addAction(
                self.page.translator('hero_edit_position'),
                lambda: self.set_edit_mode('hero'),
            )
            menu.addAction(
                self.page.translator('hero_reset'),
                self._reset_hero,
            )
        menu.exec(event.globalPos())

    def confirm_edit(self):
        """Lock the current hero/logo position and exit editing mode."""
        if self.app:
            for key in ('hero_offset', 'hero_scale', 'logo_offset', 'logo_scale'):
                self.page.update_app_field(
                    self.app, key, self.app.get(key), refresh=False
                )
        self.set_edit_mode(None)

    def _persist_image(self, path, kind):
        """Copy a chosen image into Beer's config directory."""
        config = getattr(self.page, 'config', None)
        if config is None or not self.app:
            return path
        stored = config.import_image(
            path, self.app.get('app_id', ''), kind
        )
        return stored or path

    def _choose_hero(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.page.translator('hero_change_image'), '',
            'Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)'
        )
        if path:
            path = self._persist_image(path, 'hero')
            self.app['hero_image'] = path
            self._load_pixmaps()
            self.update()
            self.page.update_app_field(self.app, 'hero_image', path, refresh=False)

    def _reset_hero(self):
        self.app['hero_offset'] = [0, 0]
        self.app['hero_scale'] = 1.0
        self.update()
        self.page.update_app_field(self.app, 'hero_offset', [0, 0], refresh=False)
        self.page.update_app_field(self.app, 'hero_scale', 1.0, refresh=False)

    def _choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.page.translator('logo_change'), '',
            'Images (*.png *.jpg *.jpeg *.webp *.bmp *.svg);;All Files (*)'
        )
        if path:
            path = self._persist_image(path, 'logo')
            # Keep the original application icon so "Use Application Icon"
            # can restore it after a custom logo was chosen.
            if 'base_icon_path' not in self.app:
                self.app['base_icon_path'] = self.app.get('icon_path', '')
                self.app['base_icon_name'] = self.app.get('icon_name', '')
            self.app['logo_image'] = path
            self.app['logo_hidden'] = False
            self.app['icon_path'] = path
            self.app['icon_name'] = ''
            self._load_pixmaps()
            self.update()
            self.page.update_app_field(
                self.app, 'logo_image', path, refresh=False
            )
            self.page.update_app_field(
                self.app, 'logo_hidden', False, refresh=False
            )
            self.page.update_app_field(
                self.app, 'base_icon_path',
                self.app.get('base_icon_path', ''), refresh=False
            )
            self.page.update_app_field(
                self.app, 'base_icon_name',
                self.app.get('base_icon_name', ''), refresh=False
            )
            # The logo is also the application icon in lists and shelves.
            self.page.update_app_field(
                self.app, 'icon_path', path, refresh=True
            )

    def _use_app_icon(self):
        base_path = self.app.get(
            'base_icon_path', self.app.get('icon_path', '')
        )
        base_name = self.app.get('base_icon_name', '')
        self.app['logo_image'] = ''
        self.app['logo_hidden'] = False
        self.app['icon_path'] = base_path
        self.app['icon_name'] = base_name
        self._load_pixmaps()
        self.update()
        self.page.update_app_field(self.app, 'logo_image', '', refresh=False)
        self.page.update_app_field(self.app, 'logo_hidden', False, refresh=False)
        self.page.update_app_field(self.app, 'icon_name', base_name, refresh=False)
        self.page.update_app_field(
            self.app, 'icon_path', base_path, refresh=True
        )

    def _no_logo_icon(self):
        self.app['logo_hidden'] = True
        self.update()
        self.page.update_app_field(self.app, 'logo_hidden', True, refresh=False)

    def _reset_logo(self):
        self.app['logo_offset'] = [0, 0]
        self.app['logo_scale'] = 1.0
        self.update()
        self.page.update_app_field(self.app, 'logo_offset', [0, 0], refresh=False)
        self.page.update_app_field(self.app, 'logo_scale', 1.0, refresh=False)


class AppDetailView(QWidget):
    """Detail page: hero, launch button, settings and terminal."""

    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page
        self.app = None
        self._updating = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.hero = HeroPanel(page)
        self.hero.setMinimumHeight(240)
        self.hero.setMaximumHeight(320)
        root.addWidget(self.hero)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(16, 10, 16, 10)
        action_row.setSpacing(14)

        self.btn_launch = QPushButton(page.translator('launch_program'))
        self.btn_launch.setMinimumWidth(150)
        self.btn_launch.setFixedHeight(42)
        self.btn_launch.setStyleSheet(
            'background-color: #4a86c8; color: white; font-weight: bold;'
            ' border-radius: 4px;'
        )
        self.btn_launch.clicked.connect(self._launch)
        action_row.addWidget(self.btn_launch)

        stats_frame = QFrame()
        stats_frame.setObjectName('statsFrame')
        stats_frame.setStyleSheet(
            'QFrame#statsFrame { background-color: rgba(128, 128, 128, 0.10);'
            ' border: 1px solid rgba(128, 128, 128, 0.30); border-radius: 6px; }'
            ' QFrame#statsFrame QLabel { background: transparent; }'
        )
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(12, 4, 12, 4)
        stats_layout.setSpacing(2)
        self.total_label = QLabel('')
        self.last_label = QLabel('')
        self.total_label.setWordWrap(True)
        self.last_label.setWordWrap(True)
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.last_label)
        action_row.addWidget(stats_frame, 1)

        self.btn_reset_stats = QPushButton(page.translator('reset_stats'))
        self.btn_reset_stats.clicked.connect(self._reset_stats)
        action_row.addWidget(self.btn_reset_stats)
        root.addLayout(action_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        # Left: program settings
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        settings_host = QWidget()
        settings_layout = QVBoxLayout(settings_host)
        settings_layout.setContentsMargins(16, 8, 16, 16)
        settings_layout.setSpacing(8)

        title = QLabel(page.translator('program_settings'))
        title.setStyleSheet('font-size: 14px; font-weight: bold;')
        settings_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.txt_exe = QLineEdit()
        self.txt_exe.editingFinished.connect(self._on_exe_changed)
        form.addRow(page.translator('program_path'), self._with_browse(
            self.txt_exe, self._browse_exe
        ))

        self.txt_run_dir = QLineEdit()
        self.txt_run_dir.editingFinished.connect(self._on_run_dir_changed)
        form.addRow(page.translator('run_directory'), self._with_browse(
            self.txt_run_dir, self._browse_run_dir
        ))

        self.combo_arch = BeerComboBox()
        self.combo_arch.addItem(page.translator('arch_auto'), 'auto')
        self.combo_arch.addItem(page.translator('arch_32'), '32')
        self.combo_arch.addItem(page.translator('arch_64'), '64')
        self.combo_arch.currentIndexChanged.connect(self._on_arch_changed)
        form.addRow(page.translator('architecture'), self.combo_arch)

        more_row = QHBoxLayout()
        self.btn_more = QPushButton(page.translator('more_options'))
        self.btn_more.clicked.connect(self._open_more_options)
        more_row.addWidget(self.btn_more)
        self.lbl_more = QLabel('')
        self.lbl_more.setStyleSheet('color: gray; font-size: 10px;')
        more_row.addWidget(self.lbl_more, 1)
        more_host = QWidget()
        more_host.setLayout(more_row)
        more_row.setContentsMargins(0, 0, 0, 0)
        form.addRow(page.translator('more_options'), more_host)

        self.combo_runtime = BeerComboBox()
        self.combo_runtime.currentIndexChanged.connect(self._on_runtime_changed)
        form.addRow(page.translator('proton_version'), self.combo_runtime)

        self.txt_name = QLineEdit()
        self.txt_name.editingFinished.connect(self._on_name_changed)
        enable_ime(self.txt_name)
        form.addRow(page.translator('custom_name'), self.txt_name)

        self.txt_description = QLineEdit()
        self.txt_description.editingFinished.connect(self._on_description_changed)
        enable_ime(self.txt_description)
        form.addRow(page.translator('edit_desc'), self.txt_description)

        self.txt_tags = QLineEdit()
        self.txt_tags.setPlaceholderText(page.translator('tags_placeholder'))
        self.txt_tags.editingFinished.connect(self._on_tags_changed)
        enable_ime(self.txt_tags)
        form.addRow(page.translator('categories'), self.txt_tags)

        settings_layout.addLayout(form)
        settings_layout.addStretch()
        settings_scroll.setWidget(settings_host)

        # Right: terminal
        terminal_host = QWidget()
        terminal_layout = QVBoxLayout(terminal_host)
        terminal_layout.setContentsMargins(10, 8, 16, 16)
        terminal_layout.setSpacing(6)
        terminal_header = QHBoxLayout()
        terminal_title = QLabel(page.translator('terminal_log'))
        terminal_title.setStyleSheet('font-weight: bold;')
        terminal_header.addWidget(terminal_title)
        terminal_header.addStretch()
        self.btn_clear_log = QPushButton(page.translator('clear_log'))
        self.btn_clear_log.clicked.connect(lambda: self.log_output.clear())
        terminal_header.addWidget(self.btn_clear_log)
        terminal_layout.addLayout(terminal_header)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(5000)
        font = QFont('Monospace')
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.log_output.setFont(font)
        terminal_layout.addWidget(self.log_output, 1)

        splitter.addWidget(settings_scroll)
        splitter.addWidget(terminal_host)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([560, 380])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------
    def _with_browse(self, line_edit, callback):
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(line_edit, 1)
        button = QPushButton(self.page.translator('browse'))
        button.clicked.connect(callback)
        layout.addWidget(button)
        return host

    # ------------------------------------------------------------------
    def set_app(self, app):
        self.app = app
        self._updating = True
        self.hero.set_app(app)

        self.txt_exe.setText(app.get('exe_path', ''))
        self.txt_run_dir.setText(app.get('run_directory', ''))
        index = self.combo_arch.findData(str(app.get('architecture', 'auto')))
        self.combo_arch.setCurrentIndex(index if index >= 0 else 0)
        self.txt_name.setText(app.get('name', ''))
        self.txt_description.setText(app.get('description', ''))
        self.txt_tags.setText(', '.join(app.get('tags') or []))

        self._populate_runtimes(app)

        more_options = app.get('more_options') or {}
        args = more_options.get('startup_args', '') or ''
        wine = more_options.get('wine_options') or {}
        summary_parts = []
        if args:
            summary_parts.append(args)
        if wine:
            summary_parts.append(
                self.page.translator('wine_options_count').format(count=len(wine))
            )
        self.lbl_more.setText(' · '.join(summary_parts))
        self.lbl_more.setToolTip('\n'.join(summary_parts))

        self._updating = False
        self.update_stats()

    def _populate_runtimes(self, app):
        self.combo_runtime.blockSignals(True)
        self.combo_runtime.clear()
        self.combo_runtime.addItem(
            self.page.translator('native_linux_app'), NATIVE_DATA
        )
        for runtime in self.page.get_runtimes():
            label = '{} · {} ({})'.format(
                runtime.get('name', ''),
                runtime.get('version_str', ''),
                self.page.translator(
                    'runtime_type_' + runtime.get('type', 'proton')
                ),
            )
            self.combo_runtime.addItem(label, runtime.get('path', ''))

        current_path = app.get('proton_path', '')
        index = self.combo_runtime.findData(current_path) if current_path else -1
        if app.get('native'):
            self.combo_runtime.setCurrentIndex(0)
        elif index >= 0:
            self.combo_runtime.setCurrentIndex(index)
        else:
            if current_path:
                self.combo_runtime.insertItem(
                    1, os.path.basename(current_path) or current_path, current_path
                )
                self.combo_runtime.setCurrentIndex(1)
            else:
                self.combo_runtime.setCurrentIndex(1 if self.combo_runtime.count() > 1 else 0)
        self.combo_runtime.blockSignals(False)

    def update_stats(self):
        if not self.app:
            return
        translator = self.page.translator
        from ui.pages.app_helpers import format_duration
        self.total_label.setText(
            '{}: {}'.format(
                translator('total_runtime'),
                format_duration(self.app.get('total_runtime', 0), translator),
            )
        )
        last_value = self.app.get('last_launched', '')
        last_text = translator('never_used')
        if last_value:
            try:
                moment = datetime.datetime.fromisoformat(last_value)
                last_text = moment.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                last_text = last_value
        self.last_label.setText(
            '{}: {}'.format(translator('last_runtime'), last_text)
        )

    def append_log(self, text, level='info'):
        if not text:
            return
        self.log_output.appendPlainText(text.rstrip('\n'))

    def clear(self):
        self.app = None
        self.hero.set_app(None)
        self.log_output.clear()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _launch(self):
        if self.app:
            self.page.launch_app(self.app)
            self.update_stats()

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.page.translator('select_exe'), '',
            'Windows (*.exe);;All Files (*)'
        )
        if path:
            self.txt_exe.setText(path)
            self._on_exe_changed()

    def _browse_run_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, self.page.translator('select_directory'),
            self.txt_run_dir.text() or '',
        )
        if directory:
            self.txt_run_dir.setText(directory)
            self._on_run_dir_changed()

    def _save(self, key, value, refresh=True):
        if self.app is None:
            return
        self.page.update_app_field(self.app, key, value, refresh=refresh)

    def _on_exe_changed(self):
        if self._updating or self.app is None:
            return
        self._save('exe_path', self.txt_exe.text().strip(), refresh=False)
        if self.app.get('native'):
            value = self.txt_exe.text().strip()
            self._save('exec_cmd', shlex.quote(value) if value else '', refresh=False)
        if not self.txt_run_dir.text().strip():
            directory = os.path.dirname(self.txt_exe.text().strip())
            self.txt_run_dir.setText(directory)
            self._save('run_directory', directory, refresh=False)

    def _on_run_dir_changed(self):
        if self._updating or self.app is None:
            return
        self._save('run_directory', self.txt_run_dir.text().strip(), refresh=False)

    def _on_arch_changed(self, _index):
        if self._updating or self.app is None:
            return
        self._save('architecture', self.combo_arch.currentData() or 'auto')

    def _on_name_changed(self):
        if self._updating or self.app is None:
            return
        new_name = self.txt_name.text().strip()
        if not new_name or new_name == self.app.get('name'):
            self.txt_name.setText(self.app.get('name', ''))
            return
        if not self.page.rename_app(self.app, new_name):
            self.txt_name.setText(self.app.get('name', ''))

    def _on_description_changed(self):
        if self._updating or self.app is None:
            return
        self._save('description', self.txt_description.text().strip())

    def _on_tags_changed(self):
        if self._updating or self.app is None:
            return
        raw = self.txt_tags.text().replace('，', ',')
        tags = []
        for part in raw.replace(';', ',').split(','):
            tag = part.strip()
            if tag and tag not in tags:
                tags.append(tag)
        self._save('tags', tags)

    def _reset_stats(self):
        if self.app is None:
            return
        self.app['total_runtime'] = 0
        self.app['last_launched'] = ''
        self._save('total_runtime', 0, refresh=False)
        self._save('last_launched', '', refresh=False)
        self.update_stats()

    def _on_runtime_changed(self, _index):
        if self._updating or self.app is None:
            return
        data = self.combo_runtime.currentData()
        if data == NATIVE_DATA:
            self.app['native'] = True
            self.app['proton_path'] = ''
            self.app['runtime_type'] = ''
            self._save('native', True)
            self._save('proton_path', '', refresh=False)
            self._save('runtime_type', '', refresh=False)
            return

        path = data or ''
        runtime = detect_runtime(path)
        if runtime is None and path:
            QMessageBox.warning(
                self, self.page.translator('warning'),
                self.page.translator('runtime_invalid')
            )
            self._populate_runtimes(self.app)
            return
        self.app['native'] = False
        self.app['proton_path'] = path
        self.app['runtime_type'] = runtime.get('type', '') if runtime else ''
        self._save('native', False)
        self._save('proton_path', path, refresh=False)
        self._save('runtime_type', self.app['runtime_type'], refresh=False)

    def _open_more_options(self):
        if self.app is None:
            return
        dialog = MoreOptionsDialog(
            self.app.get('more_options', {}) or {}, self.page.translator, self
        )
        if dialog.exec():
            options = dialog.get_options()
            self.app['more_options'] = options
            self._save('more_options', options)
            args = options.get('startup_args', '') or ''
            wine = options.get('wine_options') or {}
            parts = []
            if args:
                parts.append(args)
            if wine:
                parts.append(
                    self.page.translator('wine_options_count').format(
                        count=len(wine)
                    )
                )
            self.lbl_more.setText(' · '.join(parts))
