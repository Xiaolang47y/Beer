# -*- coding: utf-8 -*-
"""
Saved applications page for Beer
"""

import os
import shlex

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QMenu,
    QMessageBox, QFileDialog, QDialog, QDialogButtonBox, QComboBox,
    QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap

from core.app_icon import get_app_icon
from core.desktop_generator import (
    DesktopGenerator, sanitize_filename, get_default_icon_path,
)
from core.winetricks_manager import prefix_for_name
from ui.dialogs.desktop_dialog import DesktopEntryDialog
from ui.dialogs.winetricks_dialog import WinetricksDialog
from ui.icon_extract_task import IconExtractTask


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


class ProtonSelectionDialog(QDialog):
    """Dialog to select a Proton version from a combo box, with browse option"""

    def __init__(self, current_path, proton_versions, translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self._browse_path = ''
        self.setWindowTitle(translator('select_runtime'))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.combo = QComboBox()
        for proton in proton_versions:
            self.combo.addItem(proton.get('name', proton.get('path', '')), proton.get('path', ''))

        # Browse option
        self.combo.addItem(translator('browse') + '...', '__browse__')

        # Set current
        if current_path:
            index = self.combo.findData(current_path)
            if index >= 0:
                self.combo.setCurrentIndex(index)
            else:
                # Add current path as a custom item at the top
                self.combo.insertItem(0, os.path.basename(current_path), current_path)
                self.combo.setCurrentIndex(0)

        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if self.combo.currentData() == '__browse__':
            directory = QFileDialog.getExistingDirectory(
                self, self.translator('select_proton')
            )
            if directory:
                self._browse_path = directory
                self.accept()
            # Otherwise keep dialog open
        else:
            self.accept()

    def get_proton_path(self):
        if self.combo.currentData() == '__browse__':
            return self._browse_path
        return self.combo.currentData()


class EditableProtonLabel(QLabel):
    """A label showing the Proton layer; double-click opens a selection dialog"""
    proton_changed = pyqtSignal(str)

    def __init__(self, proton_path='', proton_versions=None, translator=None, parent=None):
        super().__init__(parent)
        self.translator = translator
        self._proton_path = proton_path
        self._proton_versions = proton_versions or []
        self._editing = False
        self._update_text()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setStyleSheet(
            "QLabel {"
            " background-color: #2b2b2b;"
            " border: 1px solid #555555;"
            " border-radius: 4px;"
            " padding: 4px 6px;"
            " color: #4a86c8;"
            " font-size: 10px;"
            " }"
        )

    def _update_text(self):
        not_set = self.translator('not_set') if self.translator else 'Not set'
        if self._proton_path:
            name = os.path.basename(self._proton_path)
            label = self.translator('runtime_short') if self.translator else 'Runtime'
            self.setText(f"{label}: {name}")
        else:
            label = self.translator('runtime_short') if self.translator else 'Runtime'
            self.setText(f"{label}: {not_set}")

    def set_proton_path(self, path):
        self._proton_path = path
        self._update_text()

    def mouseDoubleClickEvent(self, event):
        if self._editing:
            return
        self._editing = True
        dialog = ProtonSelectionDialog(
            self._proton_path, self._proton_versions, self.translator, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_path = dialog.get_proton_path()
            if new_path:
                self._proton_path = new_path
                self._update_text()
                self.proton_changed.emit(new_path)
        self._editing = False


class AppCard(QFrame):
    """Application card widget"""

    def __init__(self, app, translator, proton_versions=None, parent=None):
        super().__init__(parent)
        self.app = app
        self.translator = translator
        self._proton_versions = proton_versions or []
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
        self.setFixedSize(180, 250)

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
        if exe_path:
            desc_text = self.app.get('description', '') or os.path.basename(exe_path)
        else:
            desc_text = self.app.get('description', '') or ''
        self.desc_label = EditableLabel(desc_text, self.translator('edit_desc'))
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.desc_label)

        # Proton layer (editable on double-click)
        self.proton_label = EditableProtonLabel(
            proton_path=self.app.get('proton_path', ''),
            proton_versions=self._proton_versions,
            translator=self.translator,
            parent=self
        )
        layout.addWidget(self.proton_label)

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

        # Try to extract from EXE (uses persistent cache)
        if exe_path and os.path.exists(exe_path):
            from core.icon_extractor import IconExtractor
            # Use the shared parent page's extractor if available (cached)
            parent_page = self.parent()
            while parent_page and not isinstance(parent_page, SavedAppsPage):
                parent_page = parent_page.parent()
            extractor = getattr(parent_page, '_icon_extractor', None) if parent_page else None
            if extractor is None:
                extractor = IconExtractor()
            if extractor.is_tool_available():
                temp_icon, error = extractor.extract_icon(exe_path)
                if temp_icon and os.path.exists(temp_icon):
                    pixmap = QPixmap(temp_icon)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.icon_label.setPixmap(scaled)
                        return

        # Fallback: beer emoji icon
        pixmap = get_app_icon().pixmap(max_size, max_size)
        if not pixmap.isNull():
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText("🍺")
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
        self._icon_tasks = []

        # Shared icon extractor (cached tool checks)
        from core.icon_extractor import IconExtractor
        self._icon_extractor = IconExtractor(
            icons_dir=config.get_icons_dir() if hasattr(config, 'get_icons_dir') else None
        )

        self.init_ui()
        self.load_apps()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        self.title = QLabel(self.translator('saved_apps'))
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title)

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
        self.desc = QLabel(self.translator('saved_apps_desc'))
        self.desc.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.desc)

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
        runtime_versions = []
        try:
            mp = self.main_window.main_page
            if mp and mp.proton_manager:
                runtime_versions = mp.proton_manager.get_runtimes()
        except Exception:
            pass

        card = AppCard(app, self.translator, runtime_versions, self)

        # Double-click icon to launch
        card.icon_label.mouseDoubleClickEvent = lambda e, a=app: self.launch_app(a)

        # Name changed
        card.name_label.text_changed.connect(
            lambda new_name, a=app, c=card: self._on_name_changed(a, new_name, c)
        )

        # Description changed
        card.desc_label.text_changed.connect(lambda new_desc, a=app: self._on_desc_changed(a, new_desc))

        # Proton/Wine runtime changed
        card.proton_label.proton_changed.connect(lambda new_path, a=app: self._on_proton_changed(a, new_path))

        # Context menu
        card.customContextMenuRequested.connect(lambda pos, a=app, c=card: self.show_context_menu(pos, a, c))

        return card

    def _on_proton_changed(self, app, new_path):
        """Handle Proton/Wine runtime change."""
        from core.runtime_utils import detect_runtime

        runtime = detect_runtime(new_path)
        if runtime is None:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('runtime_invalid')
            )
            return

        # Only remember paths that are not already found by the automatic scan.
        main_page = getattr(self.main_window, 'main_page', None)
        known_paths = []
        if main_page and main_page.proton_manager:
            known_paths = [
                item.get('path', '') for item in main_page.proton_manager.get_runtimes()
            ]
        custom_paths = list(self.config.get('custom_proton_paths', []))
        if runtime.get('path') not in known_paths and runtime.get('path') not in custom_paths:
            custom_paths.append(runtime.get('path'))
            self.config.set('custom_proton_paths', custom_paths)

        app['proton_path'] = new_path
        self.config._save_apps()

        if main_page and main_page.proton_manager:
            main_page.load_proton_versions()
            main_page.select_runtime_path(new_path)

        self.main_window.log_message(
            f"Runtime updated for {app.get('name', '')}: {new_path}", 'info'
        )

    def _on_name_changed(self, app, new_name, card=None):
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
                # Revert both the data and the visible label.
                app['name'] = old_name
                if card is not None:
                    card.name_label.setText(old_name)
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
        exe_path = app.get('exe_path')
        working_dir = app.get('run_directory')
        runtime_path = app.get('proton_path', '')

        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('exe_not_found')
            )
            return

        manager = getattr(self.main_window.main_page, 'proton_manager', None)
        if manager is None:
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('runtime_missing')
            )
            return

        runtime = manager.get_runtime_by_path(runtime_path)
        if runtime is None:
            runtime = manager.get_runtimes()[0] if manager.get_runtimes() else None
        if runtime is None:
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('runtime_select_first')
            )
            return

        env_vars = self.config.get('environment_variables', {})
        more_options = app.get('more_options', {}) or {}
        args_text = more_options.get('startup_args', '') or ''
        args = shlex.split(args_text) if args_text.strip() else None
        wine_options = more_options.get('wine_options', {}) or {}

        if self.config.get('show_log_on_start', False):
            self.main_window.show_log()

        success, result = manager.launch_program(
            runtime.get('path', ''), exe_path, working_dir, env_vars, args,
            output_callback=self.main_window.log_message,
            wine_options=wine_options,
            architecture=app.get('architecture', 'auto'),
        )

        if success:
            self.main_window.log_message(f"Launched: {app.get('name')}", 'success')
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

        winetricks_action = QAction(self.translator('open_winetricks'), self)
        winetricks_action.triggered.connect(lambda: self.open_winetricks(app))
        menu.addAction(winetricks_action)

        menu.addSeparator()

        edit_action = QAction(self.translator('edit'), self)
        edit_action.triggered.connect(lambda: self.edit_app(app))
        menu.addAction(edit_action)

        delete_action = QAction(self.translator('delete'), self)
        delete_action.triggered.connect(lambda: self.delete_app(app))
        menu.addAction(delete_action)

        menu.exec(card.mapToGlobal(pos))

    def open_winetricks(self, app):
        """Open Winetricks for a saved application."""
        manager = getattr(self.main_window.main_page, 'proton_manager', None)
        if manager is None or not manager.get_runtimes():
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('runtime_select_first')
            )
            return

        prefix = prefix_for_name(self.config, app.get('name', 'default'))
        dialog = WinetricksDialog(
            self.translator,
            runtimes=manager.get_runtimes(),
            config=self.config,
            parent=self,
            app_name=app.get('name', ''),
            runtime_path=app.get('proton_path', ''),
            prefix=prefix,
        )
        dialog.exec()

    def add_desktop_shortcut(self, app):
        """Add a desktop shortcut for the app."""
        name = app.get('name', '')
        exe_path = app.get('exe_path', '')

        if not name or not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('desktop_name_exe_required')
            )
            return

        icon_path = app.get('icon_path', '')
        if icon_path and os.path.exists(icon_path):
            self._open_shortcut_dialog(app, icon_path)
            return

        if self._icon_extractor.is_tool_available():
            self._extract_shortcut_icon_async(app)
        else:
            self._open_shortcut_dialog(app, get_default_icon_path())

    def _extract_shortcut_icon_async(self, app):
        """Extract the icon in the background before opening the dialog."""
        progress = QProgressDialog(
            self.translator('extracting_icon'), None, 0, 0, self
        )
        progress.setWindowTitle(self.translator('please_wait'))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()

        task = IconExtractTask(
            self._icon_extractor, app.get('exe_path', ''), self
        )
        self._icon_tasks.append(task)

        def done(icon_path, error):
            progress.close()
            progress.deleteLater()
            if task in self._icon_tasks:
                self._icon_tasks.remove(task)
            task.deleteLater()
            if error:
                self.main_window.log_message(
                    f"{self.translator('icon_extraction_failed')}: {error}",
                    'warning'
                )
            self._open_shortcut_dialog(
                app, icon_path or get_default_icon_path()
            )

        task.extracted.connect(done)
        task.start()

    def _open_shortcut_dialog(self, app, icon_path=''):
        name = app.get('name', '')
        exe_path = app.get('exe_path', '')
        working_dir = app.get('run_directory', '')
        description = app.get('description', '')

        more_options = app.get('more_options', {}) or {}
        args_text = more_options.get('startup_args', '') or ''
        manager = getattr(self.main_window.main_page, 'proton_manager', None)
        runtimes = manager.get_runtimes() if manager else []

        options = {
            'name': name,
            'comment': description or name,
            'exe_path': exe_path,
            'working_dir': working_dir,
            'runtime_path': app.get('proton_path', ''),
            'icon_path': icon_path,
            'args': args_text,
            'categories': 'Game;',
            'terminal': False,
            'target': 'desktop',
            'filename': sanitize_filename(name) + '.desktop',
        }

        dialog = DesktopEntryDialog(
            options,
            self.translator,
            runtimes=runtimes,
            icon_extractor=self._icon_extractor,
            parent=self,
        )
        dialog.set_runtime_context(
            env_vars=self.config.get('environment_variables', {}),
            wine_options=more_options.get('wine_options', {}) or {},
        )
        if not dialog.exec():
            return

        desktop_options = dialog.get_options()
        generator = DesktopGenerator()
        success, result = generator.generate_desktop_file(
            **desktop_options,
            env_vars=self.config.get('environment_variables', {}),
            wine_options=more_options.get('wine_options', {}) or {},
            translator=self.translator,
        )

        if success:
            app['desktop_options'] = desktop_options
            self.config._save_apps()
            self.main_window.log_message(
                f"{self.translator('desktop_file_generated')}: {result}",
                'success'
            )
            QMessageBox.information(
                self,
                self.translator('success'),
                f"{self.translator('desktop_file_generated')}\n{result}"
            )
        else:
            self.main_window.log_message(
                f"{self.translator('desktop_generation_failed')}: {result}", 'error'
            )
            QMessageBox.warning(
                self,
                self.translator('error'),
                f"{self.translator('desktop_generation_failed')}\n{result}"
            )

    def edit_app(self, app):
        """Edit an application configuration"""
        # Switch to main page and load config
        self.main_window.show_page(0)
        main_page = self.main_window.main_page

        main_page.program_name.setText(app.get('name', ''))
        main_page.program_path.setText(app.get('exe_path', ''))
        main_page.run_directory.setText(app.get('run_directory', ''))

        # Set runtime in the main page runtime table
        proton_path = app.get('proton_path', '')
        if proton_path:
            main_page.select_runtime_path(proton_path)

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
        # Update header texts
        self.title.setText(self.translator('saved_apps'))
        self.search_box.setPlaceholderText(self.translator('search'))
        self.btn_import.setText(self.translator('import'))
        self.btn_export.setText(self.translator('export'))
        self.desc.setText(self.translator('saved_apps_desc'))
        self.empty_label.setText(self.translator('no_saved_apps'))

        # Reload grid so cards use the new translator
        self.load_apps()
