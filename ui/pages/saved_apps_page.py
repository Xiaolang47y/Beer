# -*- coding: utf-8 -*-
"""
Saved applications page for Beer
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QMenu,
    QMessageBox, QFileDialog, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap


class SimpleInputDialog(QDialog):
    """A minimal dialog with only a title and a text input field"""

    def __init__(self, title='', default_text='', parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.input_field = QLineEdit(default_text)
        self.input_field.selectAll()
        layout.addWidget(self.input_field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.input_field.text()


class EditableLabel(QLabel):
    """A label that becomes editable on double-click"""
    text_changed = pyqtSignal(str)

    def __init__(self, text='', dialog_title='', parent=None):
        super().__init__(text, parent)
        self._editing = False
        self._dialog_title = dialog_title

    def mouseDoubleClickEvent(self, event):
        if self._editing:
            return
        self._editing = True
        current_text = self.text()
        dialog = SimpleInputDialog(self._dialog_title, current_text, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_text = dialog.get_text()
            if new_text.strip():
                self.setText(new_text.strip())
                self.text_changed.emit(new_text.strip())
        self._editing = False


class AppCard(QFrame):
    """Application card widget"""

    def __init__(self, app, translator, parent=None):
        super().__init__(parent)
        self.app = app
        self.translator = translator
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #3c3f41;
                border: 1px solid #555555;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #4c4f51;
                border: 1px solid #4a86c8;
            }
        """)
        self.setFixedSize(180, 220)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        # Icon (double-click to launch)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setScaledContents(False)
        self.icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_label.setToolTip(self.translator('double_click_launch'))

        # Load EXE icon
        exe_path = self.app.get('exe_path', '')
        icon_path = self.app.get('icon_path', '')
        self._load_icon(exe_path, icon_path)

        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Name (editable)
        self.name_label = EditableLabel(self.app.get('name', 'Unknown'), self.translator('edit_name'))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #ffffff;")
        self.name_label.setWordWrap(True)
        self.name_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.name_label)

        # Description (editable)
        desc_text = self.app.get('description', '') or os.path.basename(exe_path) if exe_path else ''
        self.desc_label = EditableLabel(desc_text, self.translator('edit_desc'))
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.desc_label)

        layout.addStretch()

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _load_icon(self, exe_path, icon_path):
        """Load icon from icon_path or extract from exe_path"""
        max_size = 56  # Leave some padding inside the 64x64 label

        # Try saved icon path first
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.icon_label.setPixmap(scaled)
                return

        # Try to extract from EXE
        if exe_path and os.path.exists(exe_path):
            from core.icon_extractor import IconExtractor
            extractor = IconExtractor()
            if extractor.is_tool_available():
                temp_icon, error = extractor.extract_icon(exe_path)
                if temp_icon and os.path.exists(temp_icon):
                    pixmap = QPixmap(temp_icon)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.icon_label.setPixmap(scaled)
                        return

        # Fallback
        app_icon = QIcon.fromTheme('application-x-executable')
        if not app_icon.isNull():
            self.icon_label.setPixmap(app_icon.pixmap(max_size, max_size))
        else:
            self.icon_label.setText("")
            self.icon_label.setStyleSheet("font-size: 32px; color: #ffffff;")


class SavedAppsPage(QWidget):
    """Saved applications page widget"""

    def __init__(self, config, translator, main_window):
        super().__init__()
        self.config = config
        self.translator = translator
        self.main_window = main_window

        self.apps = []
        self.filtered_apps = []

        self.init_ui()
        self.load_apps()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel(self.translator('saved_apps'))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.translator('search'))
        self.search_box.setFixedWidth(200)
        self.search_box.textChanged.connect(self.filter_apps)
        header_layout.addWidget(self.search_box)

        # Import button
        self.btn_import = QPushButton(self.translator('import'))
        self.btn_import.clicked.connect(self.import_apps)
        header_layout.addWidget(self.btn_import)

        # Export button
        self.btn_export = QPushButton(self.translator('export'))
        self.btn_export.clicked.connect(self.export_apps)
        header_layout.addWidget(self.btn_export)

        layout.addLayout(header_layout)

        # Description
        desc = QLabel(self.translator('saved_apps_desc'))
        desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(desc)

        # Scroll area for grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Grid widget
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

        # Empty label
        self.empty_label = QLabel(self.translator('no_saved_apps'))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-size: 14px; padding: 50px;")
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def load_apps(self):
        """Load saved applications"""
        self.apps = self.config.get_apps()
        self.filtered_apps = self.apps
        self.refresh_grid()

    def refresh_grid(self):
        """Refresh the grid view"""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show empty label if no apps
        if not self.filtered_apps:
            self.empty_label.show()
            self.grid_widget.hide()
            return

        self.empty_label.hide()
        self.grid_widget.show()

        # Add apps to grid
        cols = 4
        for i, app in enumerate(self.filtered_apps):
            card = self._create_app_card(app)
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)

    def _create_app_card(self, app):
        """Create an application card"""
        card = AppCard(app, self.translator, self)

        # Double-click icon to launch
        card.icon_label.mouseDoubleClickEvent = lambda e, a=app: self.launch_app(a)

        # Name changed
        card.name_label.text_changed.connect(lambda new_name, a=app: self._on_name_changed(a, new_name))

        # Description changed
        card.desc_label.text_changed.connect(lambda new_desc, a=app: self._on_desc_changed(a, new_desc))

        # Context menu
        card.customContextMenuRequested.connect(lambda pos, a=app, c=card: self.show_context_menu(pos, a, c))

        return card

    def _on_name_changed(self, app, new_name):
        """Handle name change"""
        old_name = app.get('name', '')
        # Check for duplicate
        for other in self.apps:
            if other.get('name') == new_name and other is not app:
                QMessageBox.warning(
                    self,
                    self.translator('warning'),
                    self.translator('name_exists')
                )
                # Revert
                app['name'] = old_name
                return

        app['name'] = new_name
        self.config._save_apps()
        self.main_window.log_message(f"Renamed: {old_name} -> {new_name}", 'info')

    def _on_desc_changed(self, app, new_desc):
        """Handle description change"""
        app['description'] = new_desc
        self.config._save_apps()

    def launch_app(self, app):
        """Launch an application"""
        from core.proton_manager import ProtonManager

        proton_path = app.get('proton_path')
        exe_path = app.get('exe_path')
        working_dir = app.get('run_directory')

        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('exe_not_found')
            )
            return

        if not proton_path:
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('proton_not_found')
            )
            return

        # Launch
        proton_manager = ProtonManager()
        env_vars = self.config.get('environment_variables', {})
        more_options = app.get('more_options', {})
        args = more_options.get('startup_args', '').split() if more_options.get('startup_args') else None

        success, result = proton_manager.launch_program(
            proton_path, exe_path, working_dir, env_vars, args
        )

        if success:
            self.main_window.log_message(f"Launched: {app.get('name')}", 'success')
            self.main_window.show_log()
        else:
            self.main_window.log_message(f"Failed to launch: {result}", 'error')

    def show_context_menu(self, pos, app, card):
        """Show context menu for app card"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #4a86c8;
            }
        """)

        launch_action = QAction(self.translator('run'), self)
        launch_action.triggered.connect(lambda: self.launch_app(app))
        menu.addAction(launch_action)

        # Add desktop shortcut
        shortcut_action = QAction(self.translator('add_shortcut'), self)
        shortcut_action.triggered.connect(lambda: self.add_desktop_shortcut(app))
        menu.addAction(shortcut_action)

        menu.addSeparator()

        edit_action = QAction(self.translator('edit'), self)
        edit_action.triggered.connect(lambda: self.edit_app(app))
        menu.addAction(edit_action)

        delete_action = QAction(self.translator('delete'), self)
        delete_action.triggered.connect(lambda: self.delete_app(app))
        menu.addAction(delete_action)

        menu.exec(card.mapToGlobal(pos))

    def add_desktop_shortcut(self, app):
        """Add a desktop shortcut for the app"""
        from core.desktop_generator import DesktopGenerator
        from core.icon_extractor import IconExtractor

        name = app.get('name', '')
        exe_path = app.get('exe_path', '')
        proton_path = app.get('proton_path', '')
        working_dir = app.get('run_directory', '')
        description = app.get('description', '')

        if not name or not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                "Missing name or executable path"
            )
            return

        # Extract icon
        icon_path = None
        extractor = IconExtractor()
        if extractor.is_tool_available():
            icon_path, _ = extractor.extract_icon(exe_path)

        generator = DesktopGenerator()
        env_vars = self.config.get('environment_variables', {})
        more_options = app.get('more_options', {})
        args = more_options.get('startup_args', '').split() if more_options.get('startup_args') else None

        success, result = generator.generate_desktop_file(
            name=name,
            exe_path=exe_path,
            icon_path=icon_path,
            working_dir=working_dir,
            proton_path=proton_path,
            env_vars=env_vars,
            args=args,
            comment=description
        )

        if success:
            self.main_window.log_message(f"Desktop shortcut created: {result}", 'success')
            QMessageBox.information(
                self,
                self.translator('success'),
                self.translator('desktop_file_generated')
            )
        else:
            self.main_window.log_message(f"Failed to create shortcut: {result}", 'error')
            QMessageBox.warning(
                self,
                self.translator('error'),
                f"Failed: {result}"
            )

    def edit_app(self, app):
        """Edit an application configuration"""
        # Switch to main page and load config
        self.main_window.show_page(0)
        main_page = self.main_window.main_page

        main_page.program_name.setText(app.get('name', ''))
        main_page.program_path.setText(app.get('exe_path', ''))
        main_page.run_directory.setText(app.get('run_directory', ''))

        # Set Proton
        proton_path = app.get('proton_path')
        index = main_page.proton_combo.findData(proton_path)
        if index >= 0:
            main_page.proton_combo.setCurrentIndex(index)

        # Set architecture
        arch = app.get('architecture', 'auto')
        index = main_page.arch_combo.findData(arch)
        if index >= 0:
            main_page.arch_combo.setCurrentIndex(index)

        # Set more options
        main_page.more_options = app.get('more_options', {})

    def delete_app(self, app):
        """Delete an application"""
        reply = QMessageBox.question(
            self,
            self.translator('confirm_delete'),
            self.translator('confirm_delete_msg'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config.delete_app(app.get('name'))
            self.load_apps()
            self.main_window.log_message(f"Deleted: {app.get('name')}", 'info')

    def filter_apps(self, text):
        """Filter applications by search text"""
        if not text:
            self.filtered_apps = self.apps
        else:
            text_lower = text.lower()
            self.filtered_apps = [
                app for app in self.apps
                if text_lower in app.get('name', '').lower()
            ]
        self.refresh_grid()

    def import_apps(self):
        """Import applications"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('import'),
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if self.config.import_apps(file_path):
                self.load_apps()
                self.main_window.log_message("Applications imported", 'success')
            else:
                QMessageBox.warning(
                    self,
                    self.translator('error'),
                    "Failed to import applications"
                )

    def export_apps(self):
        """Export applications"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translator('export'),
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if self.config.export_apps(file_path):
                self.main_window.log_message("Applications exported", 'success')
            else:
                QMessageBox.warning(
                    self,
                    self.translator('error'),
                    "Failed to export applications"
                )

    def refresh(self):
        """Refresh the page"""
        self.load_apps()
