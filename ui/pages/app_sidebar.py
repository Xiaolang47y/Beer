# -*- coding: utf-8 -*-
"""Left sidebar and category filter panel for the library page."""

import json

from PyQt6.QtCore import QMimeData, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QPushButton, QToolButton,
    QVBoxLayout, QWidget,
)

from ui.pages.app_helpers import (
    MIME_APP,
    app_category_keys,
    enable_ime,
    fallback_app_pixmap,
    make_filter_icon,
    resolve_app_pixmap,
)
from ui.widgets import BeerComboBox

CATEGORY_ORDER = ('proton', 'wine', 'native', 'arch32', 'arch64')


class ProgramListWidget(QListWidget):
    """Program list that can be dragged onto custom shelves."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(24, 24))
        self.setFrameShape(QFrame.Shape.NoFrame)

    def mimeTypes(self):
        return [MIME_APP]

    def mimeData(self, items):
        names = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in items
            if item is not None
        ]
        data = QMimeData()
        data.setData(MIME_APP, json.dumps(names).encode('utf-8'))
        return data

    def startDrag(self, supported_actions):
        items = self.selectedItems()
        if not items:
            return
        drag = QDrag(self)
        drag.setMimeData(self.mimeData(items))
        icon = items[0].icon()
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(48, 48))
        drag.exec(Qt.DropAction.CopyAction)


class AppSidebar(QFrame):
    """Steam-like sidebar: shelf button, search, program list and add button."""

    shelf_requested = pyqtSignal()
    search_changed = pyqtSignal(str)
    filter_toggled = pyqtSignal(bool)
    app_activated = pyqtSignal(str)
    app_context_requested = pyqtSignal(list, QPoint)
    create_requested = pyqtSignal()
    import_desktop_requested = pyqtSignal()
    import_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.setObjectName('appSidebar')
        self.setFixedWidth(248)
        self.setStyleSheet("""
            QFrame#appSidebar {
                background-color: rgba(128, 128, 128, 0.10);
                border-right: 1px solid rgba(128, 128, 128, 0.30);
            }
            QFrame#appSidebar QPushButton#shelfButton {
                background: transparent;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: bold;
                padding: 6px 2px;
            }
            QFrame#appSidebar QPushButton#shelfButton:hover {
                color: #4a86c8;
            }
            QFrame#appSidebar QPushButton#addProgramButton {
                background-color: rgba(74, 134, 200, 0.25);
                border: 1px solid #4a86c8;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QFrame#appSidebar QPushButton#addProgramButton:hover {
                background-color: rgba(74, 134, 200, 0.45);
            }
            QFrame#appSidebar QLabel {
                background: transparent;
            }
            QFrame#appSidebar QListWidget {
                background: transparent;
                border: none;
            }
            QFrame#appSidebar QListWidget::item {
                padding: 5px 4px;
                border-radius: 4px;
            }
            QFrame#appSidebar QListWidget::item:selected {
                background-color: #4a86c8;
                color: #ffffff;
            }
            QFrame#appSidebar QListWidget::item:hover:!selected {
                background-color: rgba(128, 128, 128, 0.22);
            }
            QFrame#appSidebar QToolButton {
                border: 1px solid rgba(128, 128, 128, 0.45);
                border-radius: 4px;
                padding: 4px;
            }
            QFrame#appSidebar QToolButton:checked {
                background-color: rgba(74, 134, 200, 0.55);
                border-color: #4a86c8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.shelf_button = QPushButton(self.translator('library'), self)
        self.shelf_button.setObjectName('shelfButton')
        self.shelf_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.shelf_button.clicked.connect(self.shelf_requested)
        layout.addWidget(self.shelf_button)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.translator('search'))
        enable_ime(self.search_box)
        self.search_box.textChanged.connect(self.search_changed)
        search_row.addWidget(self.search_box, 1)

        self.filter_button = QToolButton()
        self.filter_button.setCheckable(True)
        self.filter_button.setIcon(make_filter_icon())
        self.filter_button.setIconSize(QSize(16, 16))
        self.filter_button.setToolTip(self.translator('filter'))
        self.filter_button.toggled.connect(self.filter_toggled)
        search_row.addWidget(self.filter_button)
        layout.addLayout(search_row)

        self.list_label = QLabel(self.translator('program_list'))
        self.list_label.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(self.list_label)

        self.program_list = ProgramListWidget()
        self.program_list.itemClicked.connect(self._on_item_activated)
        self.program_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.program_list.customContextMenuRequested.connect(
            self._on_context_menu
        )
        layout.addWidget(self.program_list, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        self.btn_add = QPushButton(self.translator('add_program'))
        self.btn_add.setObjectName('addProgramButton')
        self.btn_add.clicked.connect(self._show_add_menu)
        bottom_row.addWidget(self.btn_add, 1)

        self.menu_button = QToolButton()
        self.menu_button.setText('⋮')
        self.menu_button.setToolTip(self.translator('more_actions'))
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        bottom_row.addWidget(self.menu_button)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    def _on_item_activated(self, item):
        # Ctrl/Shift clicks build a multi-selection instead of opening detail.
        modifiers = QApplication.keyboardModifiers()
        if modifiers & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.ShiftModifier
        ):
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if name:
            self.app_activated.emit(name)

    def _on_context_menu(self, pos):
        item = self.program_list.itemAt(pos)
        if item is None:
            return
        if not item.isSelected():
            self.program_list.setCurrentItem(item)
        names = [
            selected.data(Qt.ItemDataRole.UserRole)
            for selected in self.program_list.selectedItems()
            if selected.data(Qt.ItemDataRole.UserRole)
        ]
        if names:
            self.app_context_requested.emit(
                names, self.program_list.mapToGlobal(pos)
            )

    def _show_add_menu(self):
        menu = QMenu(self)
        menu.addAction(
            self.translator('create_from_home'), self.create_requested
        )
        menu.addAction(
            self.translator('import_desktop'), self.import_desktop_requested
        )
        point = self.btn_add.mapToGlobal(
            QPoint(0, self.btn_add.height())
        )
        menu.exec(point)

    def set_apps(self, apps):
        """Populate the program list, keeping the current selection."""
        current = self.selected_app_name()
        self.program_list.blockSignals(True)
        self.program_list.clear()
        for app in apps:
            item = QListWidgetItem(app.get('name', 'Unknown'))
            pixmap = resolve_app_pixmap(app, 24)
            if pixmap.isNull():
                pixmap = fallback_app_pixmap(24)
            if not pixmap.isNull():
                from PyQt6.QtGui import QIcon
                item.setIcon(QIcon(pixmap))
            item.setData(Qt.ItemDataRole.UserRole, app.get('name', ''))
            item.setToolTip(app.get('exe_path', '') or app.get('exec_cmd', ''))
            self.program_list.addItem(item)
        self.program_list.blockSignals(False)
        if current:
            self.select_app(current)

    def select_app(self, name):
        for row in range(self.program_list.count()):
            item = self.program_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self.program_list.setCurrentItem(item)
                return
        self.program_list.clearSelection()

    def selected_app_name(self):
        item = self.program_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ''

    def set_search_text(self, text):
        self.search_box.blockSignals(True)
        self.search_box.setText(text)
        self.search_box.blockSignals(False)

    def update_texts(self):
        self.shelf_button.setText(self.translator('library'))
        self.search_box.setPlaceholderText(self.translator('search'))
        self.filter_button.setToolTip(self.translator('filter'))
        self.list_label.setText(self.translator('program_list'))
        self.btn_add.setText(self.translator('add_program'))
        self.menu_button.setToolTip(self.translator('more_actions'))


class CategoryPanel(QFrame):
    """Right-side category list that restricts the search scope."""

    filter_changed = pyqtSignal(set)
    sort_changed = pyqtSignal(str)

    def __init__(self, translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.setObjectName('categoryPanel')
        self.setFixedWidth(190)
        self.setStyleSheet("""
            QFrame#categoryPanel {
                background-color: rgba(128, 128, 128, 0.10);
                border-right: 1px solid rgba(128, 128, 128, 0.30);
            }
            QFrame#categoryPanel QLabel, QFrame#categoryPanel QCheckBox {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.title = QLabel(self.translator('category_title'))
        self.title.setStyleSheet('font-weight: bold;')
        layout.addWidget(self.title)

        self.desc = QLabel(self.translator('category_desc'))
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet('color: gray; font-size: 10px;')
        layout.addWidget(self.desc)

        self.sort_label = QLabel(self.translator('sort_by'))
        self.sort_label.setStyleSheet('color: gray; font-size: 10px;')
        layout.addWidget(self.sort_label)

        self.sort_combo = BeerComboBox()
        self.sort_combo.addItem(self.translator('sort_name'), 'name')
        self.sort_combo.addItem(self.translator('sort_runtime'), 'runtime')
        self.sort_combo.addItem(self.translator('sort_import'), 'import')
        self.sort_combo.currentIndexChanged.connect(self._emit_sort)
        layout.addWidget(self.sort_combo)

        self.checkboxes = {}
        self._tag_checkboxes = {}
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        for key in CATEGORY_ORDER:
            checkbox = QCheckBox(self.translator(f'category_{key}'))
            checkbox.toggled.connect(self._emit_filter)
            self.checkboxes[key] = checkbox
            self._container_layout.addWidget(checkbox)

        self._tag_layout = QVBoxLayout()
        self._tag_layout.setContentsMargins(0, 0, 0, 0)
        self._tag_layout.setSpacing(4)
        self._container_layout.addLayout(self._tag_layout)
        self._container_layout.addStretch()
        layout.addWidget(self._container, 1)

        self.btn_clear = QPushButton(self.translator('clear_filters'))
        self.btn_clear.clicked.connect(self.clear_selection)
        layout.addWidget(self.btn_clear)

    def _emit_filter(self, *_args):
        self.filter_changed.emit(self.selected_categories())

    def _emit_sort(self, *_args):
        self.sort_changed.emit(self.sort_combo.currentData() or 'name')

    def set_sort_mode(self, mode):
        index = self.sort_combo.findData(mode or 'name')
        if index < 0:
            index = 0
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(index)
        self.sort_combo.blockSignals(False)

    def selected_categories(self):
        selected = {
            key for key, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        }
        selected |= {
            key for key, checkbox in self._tag_checkboxes.items()
            if checkbox.isChecked()
        }
        return selected

    def clear_selection(self):
        for checkbox in list(self.checkboxes.values()) + list(
            self._tag_checkboxes.values()
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
        self.filter_changed.emit(set())

    def _set_tags(self, tags):
        """Rebuild the dynamic tag checkboxes, preserving the selection."""
        selected = {
            key for key, checkbox in self._tag_checkboxes.items()
            if checkbox.isChecked()
        }
        while self._tag_layout.count():
            item = self._tag_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._tag_checkboxes = {}

        for tag in tags:
            key = f'tag:{tag}'
            checkbox = QCheckBox(tag)
            checkbox.toggled.connect(self._emit_filter)
            if key in selected:
                checkbox.blockSignals(True)
                checkbox.setChecked(True)
                checkbox.blockSignals(False)
            self._tag_checkboxes[key] = checkbox
            self._tag_layout.addWidget(checkbox)

    def set_apps(self, apps):
        """Show only categories that exist in the current library."""
        present = set()
        tags = set()
        for app in apps:
            present |= app_category_keys(app)
            for tag in app.get('tags') or []:
                tag = str(tag).strip()
                if tag:
                    tags.add(tag)
        for key, checkbox in self.checkboxes.items():
            checkbox.setVisible(key in present)
            if key not in present and checkbox.isChecked():
                checkbox.blockSignals(True)
                checkbox.setChecked(False)
                checkbox.blockSignals(False)
        self._set_tags(sorted(tags))

    def update_texts(self):
        self.title.setText(self.translator('category_title'))
        self.desc.setText(self.translator('category_desc'))
        self.sort_label.setText(self.translator('sort_by'))
        current = self.sort_combo.currentData() or 'name'
        labels = {
            'name': self.translator('sort_name'),
            'runtime': self.translator('sort_runtime'),
            'import': self.translator('sort_import'),
        }
        for index in range(self.sort_combo.count()):
            data = self.sort_combo.itemData(index)
            self.sort_combo.setItemText(index, labels.get(data, data))
        self.set_sort_mode(current)
        for key, checkbox in self.checkboxes.items():
            checkbox.setText(self.translator(f'category_{key}'))
        self.btn_clear.setText(self.translator('clear_filters'))
