# -*- coding: utf-8 -*-
"""Steam-like shelf (library) view for saved applications."""

import json

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMenu,
    QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget,
)

from ui.pages.app_helpers import (
    MIME_APP,
    app_runtime_label,
    fallback_app_pixmap,
    format_duration,
    resolve_app_pixmap,
)

CARD_WIDTH = 180
CARD_HEIGHT = 272
CARD_SPACING = 10


class DoubleClickLabel(QLabel):
    """A label that reports double clicks to its owner."""

    double_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        # Keep single clicks on the label away from the card so that only
        # the card background opens the detail page.
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        event.accept()


class ShelfAppCard(QFrame):
    """Application tile shown inside a shelf."""

    def __init__(self, app, page, runtimes, shelf=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.page = page
        self.runtimes = runtimes
        self.shelf = shelf or {}
        self._press_pos = None
        self._drag_started = False

        self.setObjectName('shelfCard')
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setStyleSheet("""
            QFrame#shelfCard {
                background-color: rgba(128, 128, 128, 0.10);
                border: 1px solid rgba(128, 128, 128, 0.30);
                border-radius: 8px;
            }
            QFrame#shelfCard:hover {
                background-color: rgba(74, 134, 200, 0.18);
                border: 1px solid #4a86c8;
            }
            QFrame#shelfCard QLabel {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(6)

        self.icon_label = DoubleClickLabel()
        self.icon_label.setFixedSize(72, 72)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_label.setToolTip(page.translator('double_click_launch'))
        pixmap = resolve_app_pixmap(app, 64)
        if pixmap.isNull():
            pixmap = fallback_app_pixmap(64)
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText('🍺')
        self.icon_label.double_clicked.connect(lambda: self.page.launch_app(self.app))
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        name = app.get('name', 'Unknown')
        self.name_label = DoubleClickLabel(name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(40)
        self.name_label.setStyleSheet('font-weight: bold; font-size: 12px;')
        self.name_label.setToolTip(page.translator('double_click_rename'))
        self.name_label.double_clicked.connect(
            lambda: self.page.rename_app_dialog(self.app)
        )
        layout.addWidget(self.name_label)

        description = app.get('description', '') or app.get('exe_path', '')
        self.desc_label = DoubleClickLabel(description)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumHeight(32)
        self.desc_label.setStyleSheet('color: gray; font-size: 10px;')
        self.desc_label.setToolTip(page.translator('double_click_edit_desc'))
        self.desc_label.double_clicked.connect(
            lambda: self.page.edit_description(self.app)
        )
        layout.addWidget(self.desc_label)

        layout.addStretch()

        runtime_text = app_runtime_label(app, page.translator, runtimes)
        self.runtime_label = DoubleClickLabel(runtime_text)
        self.runtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.runtime_label.setWordWrap(True)
        self.runtime_label.setMaximumHeight(34)
        self.runtime_label.setStyleSheet("""
            QLabel {
                color: #4a86c8;
                background-color: rgba(74, 134, 200, 0.16);
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }
        """)
        self.runtime_label.setToolTip(page.translator('double_click_runtime'))
        self.runtime_label.double_clicked.connect(
            lambda: self.page.change_runtime(self.app)
        )
        layout.addWidget(self.runtime_label)

        played_text = format_duration(
            app.get('total_runtime', 0), page.translator
        )
        self.played_label = QLabel(
            '{}: {}'.format(page.translator('played_time'), played_text)
        )
        self.played_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.played_label.setStyleSheet("""
            QLabel {
                color: gray;
                border: 1px solid rgba(128, 128, 128, 0.45);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.played_label)

        self.customContextMenuRequested.connect(self._show_menu)
        for label in (
            self.icon_label, self.name_label, self.desc_label,
            self.runtime_label, self.played_label,
        ):
            label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            label.customContextMenuRequested.connect(
                lambda pos, widget=label: self.page.show_context_menu(
                    widget.mapToGlobal(pos), self.app, self, shelf=self.shelf
                )
            )

    def _show_menu(self, pos):
        self.page.show_context_menu(
            self.mapToGlobal(pos), self.app, self, shelf=self.shelf
        )

    # Drag the card onto a custom shelf; a plain click opens the detail page.
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._drag_started = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < (
            QApplication.startDragDistance()
        ):
            return
        drag = QDrag(self)
        data = QMimeData()
        data.setData(
            MIME_APP, json.dumps([self.app.get('name', '')]).encode('utf-8')
        )
        drag.setMimeData(data)
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(
            120, 160, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self._drag_started = True
        self._press_pos = None
        drag.exec(Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._press_pos is not None
            and not self._drag_started
        ):
            self._press_pos = None
            self.page.open_detail(self.app)
            event.accept()
            return
        self._press_pos = None
        self._drag_started = False
        super().mouseReleaseEvent(event)


class ShelfSection(QFrame):
    """One shelf row with a header and a responsive card grid."""

    def __init__(self, shelf, page, parent=None):
        super().__init__(parent)
        self.shelf = shelf
        self.page = page
        self._cards = []
        self._columns = 0
        self._drop_active = False

        self.setObjectName('shelfSection')
        self.setStyleSheet("""
            QFrame#shelfSection {
                border: 1px solid transparent;
                border-radius: 8px;
            }
            QFrame#shelfSection[dropActive="true"] {
                border: 2px dashed #4a86c8;
                background-color: rgba(74, 134, 200, 0.08);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        self.collapsed = bool(self.shelf.get('collapsed'))

        header = QHBoxLayout()
        self.collapse_button = QToolButton()
        self.collapse_button.setAutoRaise(True)
        self.collapse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        header.addWidget(self.collapse_button)

        self.title_label = QLabel(self.shelf_title())
        self.title_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        header.addWidget(self.title_label)

        self.count_label = QLabel('')
        self.count_label.setStyleSheet('color: gray; font-size: 11px;')
        header.addWidget(self.count_label)
        header.addStretch()

        self.menu_button = QToolButton()
        self.menu_button.setText('⋯')
        self.menu_button.setToolTip(page.translator('shelf_menu'))
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.setMenu(self._build_menu())
        self.menu_button.setVisible(not self.shelf.get('preset'))
        header.addWidget(self.menu_button)

        layout.addLayout(header)

        self.grid_host = QWidget()
        self.rows_layout = QVBoxLayout(self.grid_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(CARD_SPACING)
        layout.addWidget(self.grid_host)

        self.placeholder = QLabel(page.translator('shelf_empty_drop'))
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet('color: gray; font-size: 11px; padding: 24px;')
        layout.addWidget(self.placeholder)

        self.setAcceptDrops(not self.shelf.get('preset'))
        self._update_collapse_button()

    # ------------------------------------------------------------------
    def _update_collapse_button(self):
        self.collapse_button.setText('▸' if self.collapsed else '▾')
        key = 'shelf_expand' if self.collapsed else 'shelf_collapse'
        self.collapse_button.setToolTip(self.page.translator(key))

    def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.shelf['collapsed'] = self.collapsed
        self._update_collapse_button()
        self._apply_collapse()
        self.page.set_shelf_collapsed(self.shelf, self.collapsed)

    def _apply_collapse(self):
        if self.collapsed:
            self.grid_host.hide()
            self.placeholder.hide()
            return
        if getattr(self, '_apps', None):
            self.grid_host.show()
            self.placeholder.hide()
        else:
            self.grid_host.hide()
            self.placeholder.show()

    def shelf_title(self):
        preset = self.shelf.get('preset')
        if preset == 'all':
            return self.page.translator('shelf_all')
        if preset == 'recent':
            return self.page.translator('shelf_recent')
        return self.shelf.get('name') or self.page.translator('shelf_untitled')

    def _build_menu(self):
        menu = QMenu(self)
        rename = menu.addAction(self.page.translator('shelf_rename'))
        rename.triggered.connect(lambda: self.page.rename_shelf(self.shelf))
        move_up = menu.addAction(self.page.translator('shelf_move_up'))
        move_up.triggered.connect(lambda: self.page.move_shelf(self.shelf, -1))
        move_down = menu.addAction(self.page.translator('shelf_move_down'))
        move_down.triggered.connect(lambda: self.page.move_shelf(self.shelf, 1))
        menu.addSeparator()
        delete = menu.addAction(self.page.translator('shelf_delete'))
        delete.triggered.connect(lambda: self.page.delete_shelf(self.shelf))
        return menu

    def set_apps(self, apps):
        """Rebuild the card grid for the given applications."""
        self._apps = list(apps)
        self.count_label.setText(
            self.page.translator('shelf_count').format(count=len(self._apps))
        )
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards = []
        self._clear_rows()

        if not self._apps:
            self.placeholder.setText(self._empty_text())
            self._apply_collapse()
            return

        runtimes = self.page.get_runtimes()
        for app in self._apps:
            self._cards.append(
                ShelfAppCard(app, self.page, runtimes, shelf=self.shelf)
            )
        self._columns = 0
        self._relayout()
        self._apply_collapse()

    def _clear_rows(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _empty_text(self):
        if self.shelf.get('preset') == 'recent':
            return self.page.translator('shelf_recent_empty')
        if not self.shelf.get('preset'):
            return self.page.translator('shelf_empty_drop')
        return self.page.translator('no_saved_apps')

    def _relayout(self):
        available = max(1, self.width() - 32)
        columns = max(1, (available + CARD_SPACING) // (CARD_WIDTH + CARD_SPACING))
        if columns == self._columns:
            return
        self._columns = columns

        for card in self._cards:
            card.setParent(self.grid_host)
            card.hide()
        self._clear_rows()

        for start in range(0, len(self._cards), columns):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(CARD_SPACING)
            for card in self._cards[start:start + columns]:
                row_layout.addWidget(card)
                card.show()
            row_layout.addStretch()
            self.rows_layout.addWidget(row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    # ------------------------------------------------------------------
    # Drag and drop (custom shelves only)
    # ------------------------------------------------------------------
    def _set_drop_active(self, active):
        self._drop_active = active
        self.setProperty('dropActive', active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if self.shelf.get('preset'):
            return
        if event.mimeData().hasFormat(MIME_APP):
            self._set_drop_active(True)
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if self.shelf.get('preset'):
            return
        if event.mimeData().hasFormat(MIME_APP):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_drop_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if self.shelf.get('preset'):
            return
        self._set_drop_active(False)
        try:
            names = json.loads(
                bytes(event.mimeData().data(MIME_APP)).decode('utf-8')
            )
        except (ValueError, UnicodeDecodeError):
            return
        self.page.assign_apps_to_shelf(names, self.shelf.get('id'))
        event.acceptProposedAction()


class ShelfView(QWidget):
    """Scrollable list of shelves plus the thin add-shelf button."""

    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self.hint_label = QLabel(page.translator('shelf_card_hint'))
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(self.hint_label)

        self.add_shelf_button = QPushButton(page.translator('add_shelf'))
        self.add_shelf_button.setObjectName('addShelfButton')
        self.add_shelf_button.setFixedHeight(34)
        self.add_shelf_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_shelf_button.setStyleSheet("""
            QPushButton#addShelfButton {
                background: transparent;
                border: none;
                color: gray;
                text-align: center;
                padding: 0px 6px;
            }
            QPushButton#addShelfButton:hover {
                background-color: rgba(128, 128, 128, 0.16);
                border-radius: 4px;
                color: #4a86c8;
            }
        """)
        self.add_shelf_button.clicked.connect(page.create_shelf)
        layout.addWidget(self.add_shelf_button)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(18)
        self.content_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

        self._sections = []

    def set_data(self, shelves, apps):
        """Rebuild every shelf row."""
        scroll_value = self.scroll.verticalScrollBar().value()

        for section in self._sections:
            section.setParent(None)
            section.deleteLater()
        self._sections = []

        # Drop the trailing stretch before inserting new sections.
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for shelf in shelves:
            section = ShelfSection(shelf, self.page)
            section.set_apps(self._apps_for_shelf(shelf, apps))
            self.content_layout.addWidget(section)
            self._sections.append(section)
        self.content_layout.addStretch()

        self.scroll.verticalScrollBar().setValue(scroll_value)

    @staticmethod
    def _apps_for_shelf(shelf, apps):
        preset = shelf.get('preset')
        if preset == 'all':
            return list(apps)
        if preset == 'recent':
            recent = [app for app in apps if app.get('last_launched')]
            return sorted(
                recent, key=lambda app: app.get('last_launched', ''), reverse=True
            )
        shelf_id = shelf.get('id')
        return [
            app for app in apps
            if shelf_id in (app.get('shelves') or [])
        ]

    def update_texts(self):
        self.hint_label.setText(self.page.translator('shelf_card_hint'))
        self.add_shelf_button.setText(self.page.translator('add_shelf'))
