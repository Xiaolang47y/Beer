# -*- coding: utf-8 -*-
"""
Main page for Beer
"""

import os
import shlex

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QGroupBox,
    QMessageBox, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QProgressDialog, QDialog
)
from PyQt6.QtCore import Qt, QProcess, QTimer

from core.proton_manager import ProtonManager
from core.icon_extractor import IconExtractor
from core.desktop_generator import DesktopGenerator, sanitize_filename
from core.runtime_utils import (
    app_prefix_info,
    detect_runtime,
    ensure_app_prefix_fields,
)
from ui.dialogs.more_options_dialog import MoreOptionsDialog
from ui.dialogs.desktop_dialog import DesktopEntryDialog
from ui.dialogs.winetricks_dialog import WinetricksDialog
from ui.dialogs.save_app_dialog import SaveAppDialog
from ui.icon_extract_task import IconExtractTask
from ui.pages.app_helpers import enable_ime
from ui.widgets import BeerComboBox as FramelessComboBox


class MainPage(QWidget):
    """Main page widget"""

    def __init__(self, config, translator, main_window):
        super().__init__()
        self.config = config
        self.translator = translator
        self.main_window = main_window

        self.proton_manager = None
        self.desktop_generator = DesktopGenerator()
        self.icon_extractor = IconExtractor(
            icons_dir=self.config.get_icons_dir()
        )
        self.more_options = {}
        self._script_processes = []
        self._icon_tasks = []

        self.init_ui()
        self.load_proton_versions()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def init_ui(self):
        """Initialize UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Runtime selection (Proton and Wine)
        self.runtime_group = QGroupBox(self.translator('runtime_group'))
        runtime_layout = QVBoxLayout(self.runtime_group)

        self.runtime_desc = QLabel(self.translator('runtime_desc'))
        self.runtime_desc.setWordWrap(True)
        self.runtime_desc.setStyleSheet("color: gray; font-size: 11px;")
        runtime_layout.addWidget(self.runtime_desc)

        self.runtime_table = QTableWidget(0, 4)
        self.runtime_table.setHorizontalHeaderLabels([
            self.translator('runtime_name'),
            self.translator('runtime_type'),
            self.translator('runtime_version'),
            self.translator('runtime_path'),
        ])
        self.runtime_table.verticalHeader().setVisible(False)
        self.runtime_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.runtime_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.runtime_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.runtime_table.setAlternatingRowColors(True)
        self.runtime_table.setMinimumHeight(190)
        header = self.runtime_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.runtime_table.itemSelectionChanged.connect(
            self.update_runtime_buttons
        )
        runtime_layout.addWidget(self.runtime_table)

        runtime_buttons = QHBoxLayout()
        self.btn_winetricks = QPushButton(self.translator('open_winetricks'))
        self.btn_winetricks.clicked.connect(self.open_winetricks)
        runtime_buttons.addWidget(self.btn_winetricks)

        self.runtime_status = QLabel()
        self.runtime_status.setStyleSheet("color: gray; font-size: 11px;")
        runtime_buttons.addWidget(self.runtime_status)
        runtime_buttons.addStretch()

        self.btn_add_custom_runtime = QPushButton(
            self.translator('add_custom_runtime')
        )
        self.btn_add_custom_runtime.clicked.connect(self.add_custom_runtime)
        runtime_buttons.addWidget(self.btn_add_custom_runtime)

        self.btn_refresh_runtimes = QPushButton(
            self.translator('refresh_runtimes')
        )
        self.btn_refresh_runtimes.clicked.connect(self.refresh_runtimes)
        runtime_buttons.addWidget(self.btn_refresh_runtimes)

        self.btn_remove_runtime = QPushButton(self.translator('remove_runtime'))
        self.btn_remove_runtime.clicked.connect(self.remove_runtime)
        self.btn_remove_runtime.setEnabled(False)
        runtime_buttons.addWidget(self.btn_remove_runtime)

        runtime_layout.addLayout(runtime_buttons)

        self.runtime_hint = QLabel(self.translator('runtime_custom_hint'))
        self.runtime_hint.setWordWrap(True)
        self.runtime_hint.setStyleSheet("color: gray; font-size: 10px;")
        runtime_layout.addWidget(self.runtime_hint)

        layout.addWidget(self.runtime_group)

        # Program path
        self.program_group = QGroupBox(self.translator('program_path'))
        program_layout = QVBoxLayout(self.program_group)

        self.program_desc = QLabel(self.translator('program_desc'))
        self.program_desc.setWordWrap(True)
        self.program_desc.setStyleSheet("color: gray; font-size: 11px;")
        program_layout.addWidget(self.program_desc)

        program_row = QHBoxLayout()
        self.program_path = QLineEdit()
        self.program_path.setPlaceholderText("/path/to/program.exe")
        program_row.addWidget(self.program_path)

        self.btn_browse_program = QPushButton(self.translator('browse'))
        self.btn_browse_program.clicked.connect(self.browse_program)
        program_row.addWidget(self.btn_browse_program)

        program_layout.addLayout(program_row)
        layout.addWidget(self.program_group)

        # Run directory
        self.run_dir_group = QGroupBox(self.translator('run_directory'))
        run_dir_layout = QVBoxLayout(self.run_dir_group)

        self.run_dir_desc = QLabel(self.translator('run_dir_desc'))
        self.run_dir_desc.setWordWrap(True)
        self.run_dir_desc.setStyleSheet("color: gray; font-size: 11px;")
        run_dir_layout.addWidget(self.run_dir_desc)

        run_dir_row = QHBoxLayout()
        self.run_directory = QLineEdit()
        self.run_directory.setPlaceholderText("/path/to/working/directory")
        run_dir_row.addWidget(self.run_directory)
        self.program_path.editingFinished.connect(self._sync_run_directory)

        self.btn_browse_run_dir = QPushButton(self.translator('browse'))
        self.btn_browse_run_dir.clicked.connect(self.browse_run_directory)
        run_dir_row.addWidget(self.btn_browse_run_dir)

        run_dir_layout.addLayout(run_dir_row)
        layout.addWidget(self.run_dir_group)

        # Program name
        self.name_group = QGroupBox(self.translator('program_name'))
        name_layout = QVBoxLayout(self.name_group)

        self.name_desc = QLabel(self.translator('program_name_desc'))
        self.name_desc.setWordWrap(True)
        self.name_desc.setStyleSheet("color: gray; font-size: 11px;")
        name_layout.addWidget(self.name_desc)

        self.program_name = QLineEdit()
        self.program_name.setPlaceholderText("My Program")
        enable_ime(self.program_name)
        name_layout.addWidget(self.program_name)

        layout.addWidget(self.name_group)

        # Architecture selection
        self.arch_group = QGroupBox(self.translator('architecture'))
        arch_layout = QVBoxLayout(self.arch_group)

        self.arch_desc = QLabel(self.translator('arch_desc'))
        self.arch_desc.setWordWrap(True)
        self.arch_desc.setStyleSheet("color: gray; font-size: 11px;")
        arch_layout.addWidget(self.arch_desc)

        arch_row = QHBoxLayout()
        self.arch_combo = FramelessComboBox()
        self.arch_combo.addItem(self.translator('arch_auto'), 'auto')
        self.arch_combo.addItem(self.translator('arch_32'), '32')
        self.arch_combo.addItem(self.translator('arch_64'), '64')
        self.arch_combo.setMinimumWidth(150)
        arch_row.addWidget(self.arch_combo)

        self.arch_info = QLabel()
        self.arch_info.setStyleSheet("color: gray; font-size: 11px;")
        arch_row.addWidget(self.arch_info)
        arch_row.addStretch()

        arch_layout.addLayout(arch_row)

        arch_info_layout = QVBoxLayout()
        arch_info_layout.setContentsMargins(10, 5, 0, 0)

        self.info_32 = QLabel(
            f"• {self.translator('arch_32')}: {self.translator('arch_32_desc')}"
        )
        self.info_32.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_32)

        self.info_64 = QLabel(
            f"• {self.translator('arch_64')}: {self.translator('arch_64_desc')}"
        )
        self.info_64.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_64)

        self.info_auto = QLabel(
            f"• {self.translator('arch_auto')}: {self.translator('arch_auto_desc')}"
        )
        self.info_auto.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_auto)

        arch_layout.addLayout(arch_info_layout)

        layout.addWidget(self.arch_group)
        layout.addStretch()

        scroll.setWidget(main_widget)
        main_layout.addWidget(scroll)

        # Buttons (fixed at bottom, not scrolling)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(20, 10, 20, 20)

        self.btn_more_options = QPushButton(self.translator('more_options'))
        self.btn_more_options.clicked.connect(self.show_more_options)
        button_layout.addWidget(self.btn_more_options)

        self.btn_save_config = QPushButton(self.translator('save_config'))
        self.btn_save_config.clicked.connect(self.save_config)
        button_layout.addWidget(self.btn_save_config)

        self.btn_run = QPushButton(self.translator('run'))
        self.btn_run.setStyleSheet(
            "background-color: #4a86c8; color: white; font-weight: bold;"
        )
        self.btn_run.clicked.connect(self.run_program)
        button_layout.addWidget(self.btn_run)

        self.btn_generate_desktop = QPushButton(
            self.translator('generate_desktop')
        )
        self.btn_generate_desktop.clicked.connect(self.generate_desktop_file)
        button_layout.addWidget(self.btn_generate_desktop)

        main_layout.addLayout(button_layout)

    # ------------------------------------------------------------------
    # Runtime table
    # ------------------------------------------------------------------
    def load_proton_versions(self):
        """Scan and display Proton/Wine runtimes."""
        search_paths = self.config.get('proton_search_paths', [])
        wine_paths = self.config.get('wine_search_paths', []) or None
        custom_paths = self.config.get('custom_proton_paths', [])
        current_path = self.current_runtime_path()

        if self.proton_manager is None:
            self.proton_manager = ProtonManager(
                search_paths=search_paths,
                wine_search_paths=wine_paths,
                custom_paths=custom_paths,
            )
        else:
            self.proton_manager.update_paths(
                search_paths=search_paths,
                wine_search_paths=wine_paths,
                custom_paths=custom_paths,
            )

        self.populate_runtime_table(current_path)

    def populate_runtime_table(self, preferred_path=''):
        """Fill the runtime table while preserving the selected runtime."""
        runtimes = self.proton_manager.get_runtimes() if self.proton_manager else []
        self.runtime_table.setRowCount(0)

        for runtime in runtimes:
            row = self.runtime_table.rowCount()
            self.runtime_table.insertRow(row)

            name_item = QTableWidgetItem(runtime.get('name', ''))
            name_item.setData(Qt.ItemDataRole.UserRole, runtime)
            name_item.setToolTip(runtime.get('path', ''))
            self.runtime_table.setItem(row, 0, name_item)

            type_label = self.translator(
                'runtime_type_' + runtime.get('type', 'proton')
            )
            self.runtime_table.setItem(row, 1, QTableWidgetItem(type_label))
            self.runtime_table.setItem(
                row, 2, QTableWidgetItem(str(runtime.get('version_str', '')))
            )
            path_item = QTableWidgetItem(runtime.get('path', ''))
            path_item.setToolTip(runtime.get('path', ''))
            self.runtime_table.setItem(row, 3, path_item)

        if preferred_path:
            self.select_runtime_path(preferred_path)
        if not self.runtime_table.selectionModel().selectedRows() and runtimes:
            self.runtime_table.selectRow(0)

        proton_count = len([r for r in runtimes if r.get('type') == 'proton'])
        wine_count = len([r for r in runtimes if r.get('type') == 'wine'])
        if runtimes:
            self.runtime_status.setText(
                self.translator('runtime_status_count').format(
                    proton=proton_count, wine=wine_count
                )
            )
        else:
            self.runtime_status.setText(self.translator('runtime_empty_hint'))

        self.update_runtime_buttons()

    def selected_runtime(self):
        """Return the runtime dict selected in the table, or ``None``."""
        selection = self.runtime_table.selectionModel()
        if selection is None:
            return None
        rows = selection.selectedRows()
        if not rows:
            current = self.runtime_table.currentRow()
            if current < 0:
                return None
            rows = [self.runtime_table.model().index(current, 0)]
        item = self.runtime_table.item(rows[0].row(), 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def current_runtime_path(self):
        runtime = self.selected_runtime()
        return runtime.get('path', '') if runtime else ''

    def select_runtime_path(self, path):
        """Select a runtime by its path."""
        if not path:
            return
        real = os.path.realpath(path)
        for row in range(self.runtime_table.rowCount()):
            item = self.runtime_table.item(row, 0)
            if not item:
                continue
            runtime = item.data(Qt.ItemDataRole.UserRole)
            if runtime and os.path.realpath(runtime.get('path', '')) == real:
                self.runtime_table.selectRow(row)
                return

    def update_runtime_buttons(self):
        runtime = self.selected_runtime()
        self.btn_remove_runtime.setEnabled(bool(runtime and runtime.get('custom')))

    def refresh_runtimes(self):
        """Rescan runtimes and update the table."""
        self.load_proton_versions()
        count = len(self.proton_manager.get_runtimes()) if self.proton_manager else 0
        self.main_window.log_message(
            self.translator('runtime_refreshed').format(count=count), 'info'
        )

    def add_custom_runtime(self):
        """Add a custom Proton/Wine path."""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('select_runtime'),
            "",
        )
        if not directory:
            return

        if detect_runtime(directory) is None:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('runtime_invalid'),
            )
            return

        custom_paths = list(self.config.get('custom_proton_paths', []))
        if directory not in custom_paths:
            custom_paths.append(directory)
            self.config.set('custom_proton_paths', custom_paths)

        self.load_proton_versions()
        self.select_runtime_path(directory)
        self.main_window.log_message(
            f"{self.translator('runtime_added')}: {directory}", 'success'
        )

    def remove_runtime(self):
        """Remove a custom runtime path from the list."""
        runtime = self.selected_runtime()
        if not runtime:
            return
        if not runtime.get('custom'):
            QMessageBox.information(
                self,
                self.translator('info'),
                self.translator('runtime_remove_auto'),
            )
            return

        custom_root = runtime.get('custom_root') or runtime.get('path', '')
        real = os.path.realpath(custom_root)
        custom_paths = [
            path for path in self.config.get('custom_proton_paths', [])
            if os.path.realpath(path) != real
        ]
        self.config.set('custom_proton_paths', custom_paths)
        self.load_proton_versions()
        self.main_window.log_message(
            f"{self.translator('runtime_removed')}: {custom_root}", 'info'
        )

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------
    def browse_program(self):
        """Browse for an executable file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('select_exe'),
            "",
            f"{self.translator('exe_files')} (*.exe);;{self.translator('all_files')} (*)"
        )

        if file_path:
            self.program_path.setText(file_path)

            if not self.program_name.text():
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.program_name.setText(name)

            # Changing the executable always updates the working directory.
            self.run_directory.setText(os.path.dirname(file_path))

    def _sync_run_directory(self):
        """Update the working directory when the executable path changes."""
        exe_path = self.program_path.text().strip()
        if exe_path:
            self.run_directory.setText(os.path.dirname(exe_path))

    def browse_run_directory(self):
        """Browse for a run directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('select_directory')
        )

        if directory:
            self.run_directory.setText(directory)

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------
    def show_more_options(self):
        """Show the more options dialog."""
        dialog = MoreOptionsDialog(self.more_options, self.translator, self)
        if dialog.exec():
            self.more_options = dialog.get_options()

    def open_winetricks(self):
        """Open the Winetricks component manager."""
        runtime = self.selected_runtime()
        if runtime is None:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('runtime_select_first'),
            )
            return

        dialog = WinetricksDialog(
            self.translator,
            runtimes=self.proton_manager.get_runtimes() if self.proton_manager else [],
            config=self.config,
            parent=self,
            app_name=self.program_name.text().strip(),
            runtime_path=runtime.get('path', ''),
            prefix='',
        )
        dialog.exec()

    # ------------------------------------------------------------------
    # Application config
    # ------------------------------------------------------------------
    def save_config(self):
        """Save the current configuration after asking for name/categories."""
        name = self.program_name.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('name_required'),
            )
            return

        runtime = self.selected_runtime()
        if runtime is None:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('runtime_select_first'),
            )
            return

        runtime_label = '{} · {} ({})'.format(
            runtime.get('name', ''),
            runtime.get('version_str', ''),
            self.translator('runtime_type_' + runtime.get('type', 'proton')),
        )
        dialog = SaveAppDialog(
            self.translator,
            name=name,
            description=name,
            tags=[],
            runtime_label=runtime_label,
            exe_path=self.program_path.text().strip(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        name = values.get('name', '').strip()
        if not name:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('name_required'),
            )
            return

        existing_apps = self.config.get_apps()
        for app in existing_apps:
            if app.get('name') == name:
                reply = QMessageBox.question(
                    self,
                    self.translator('warning'),
                    self.translator('duplicate_name'),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                break

        app_config = self._get_app_config(icon_path='')
        app_config['name'] = name
        app_config['description'] = values.get('description', '') or name
        app_config['tags'] = values.get('tags', [])

        # Icon extraction can take a while; run it in the background so the
        # UI stays responsive and a progress dialog can be shown.
        self._extract_icon_async(
            lambda icon_path, error: self._finish_save_config(
                app_config, icon_path, error
            )
        )

    def _finish_save_config(self, app_config, icon_path, error=''):
        if error:
            self.main_window.log_message(
                f"{self.translator('icon_extraction_failed')}: {error}", 'warning'
            )
        app_config['icon_path'] = icon_path or ''
        if self.config.save_app(app_config):
            self.main_window.log_message(
                self.translator('config_saved'), 'success'
            )
            QMessageBox.information(
                self,
                self.translator('success'),
                self.translator('config_saved')
            )
            self.main_window.saved_page.refresh()

    def _extract_icon_async(self, callback):
        """Extract the current executable icon in a background thread."""
        exe_path = self.program_path.text().strip()
        if (not exe_path or not os.path.exists(exe_path)
                or not self.icon_extractor.is_tool_available()):
            callback('', '')
            return

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

        task = IconExtractTask(self.icon_extractor, exe_path, self)
        self._icon_tasks.append(task)

        def done(icon_path, error):
            progress.close()
            progress.deleteLater()
            if task in self._icon_tasks:
                self._icon_tasks.remove(task)
            task.deleteLater()
            callback(icon_path, error)

        task.extracted.connect(done)
        task.start()

    def _get_app_config(self, icon_path=''):
        """Return the current configuration as a dict."""
        runtime = self.selected_runtime()
        exe_path = self.program_path.text().strip()

        return {
            'name': self.program_name.text().strip(),
            'proton_path': runtime.get('path', '') if runtime else '',
            'runtime_type': runtime.get('type', '') if runtime else '',
            'exe_path': exe_path,
            'run_directory': self.run_directory.text().strip(),
            'architecture': self.arch_combo.currentData(),
            'more_options': self.more_options,
            'icon_path': icon_path or '',
        }

    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------
    def run_program(self):
        """Run the program with the selected Proton/Wine runtime."""
        exe_path = self.program_path.text().strip()
        if not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('exe_not_found')
            )
            return

        if not os.path.exists(exe_path):
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('exe_not_found')
            )
            return

        runtime = self.selected_runtime()
        if runtime is None:
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('runtime_select_first')
            )
            return

        pre_launch_script = self.more_options.get('pre_launch_script')
        if pre_launch_script:
            self._run_script(pre_launch_script)

        self.main_window.log_message(f"Launching: {exe_path}", 'info')
        if self.config.get('show_log_on_start', False):
            self.main_window.show_log()

        env_vars = self.config.get('environment_variables', {})
        args = self._startup_args()
        wine_options = self.more_options.get('wine_options', {}) or {}
        working_dir = self.run_directory.text().strip() or os.path.dirname(exe_path)

        success, result = self.proton_manager.launch_program(
            runtime.get('path', ''),
            exe_path,
            working_dir,
            env_vars,
            args,
            output_callback=self.main_window.log_message,
            wine_options=wine_options,
            architecture=self.arch_combo.currentData(),
        )

        if success:
            self.main_window.log_message(
                self.translator('launch_success'), 'success'
            )
            batch_apps = self.more_options.get('batch_apps', [])
            if batch_apps:
                self._batch_launch(batch_apps)
        else:
            self.main_window.log_message(
                f"{self.translator('launch_failed')}: {result}", 'error'
            )

    def _startup_args(self):
        text = self.more_options.get('startup_args', '') or ''
        if not text.strip():
            return None
        try:
            return shlex.split(text)
        except ValueError:
            return text.split()

    def _run_script(self, script_path):
        """Run a shell script asynchronously."""
        process = QProcess(self)
        self._script_processes.append(process)

        def on_output():
            text = bytes(process.readAllStandardOutput()).decode(
                'utf-8', errors='replace'
            )
            if text:
                self.main_window.log_message(text, 'info')

        def on_error():
            text = bytes(process.readAllStandardError()).decode(
                'utf-8', errors='replace'
            )
            if text:
                self.main_window.log_message(text, 'error')

        def on_finished(code, _status):
            self.main_window.log_message(
                f"Script exited with code {code}", 'info' if code == 0 else 'error'
            )
            if process in self._script_processes:
                self._script_processes.remove(process)
            process.deleteLater()

        process.readyReadStandardOutput.connect(on_output)
        process.readyReadStandardError.connect(on_error)
        process.finished.connect(on_finished)
        process.start('bash', [script_path])
        self.main_window.log_message(f"Script started: {script_path}", 'info')

    def _batch_launch(self, batch_apps, index=0):
        """Launch multiple applications in sequence."""
        if index >= len(batch_apps):
            return

        app = batch_apps[index]
        exe_path = app.get('exe_path', '')
        runtime = self.selected_runtime()
        app_runtime_path = app.get('proton_path', '')
        if app_runtime_path:
            candidate = self.proton_manager.get_runtime_by_path(app_runtime_path)
            if candidate:
                runtime = candidate

        if runtime and exe_path and os.path.exists(exe_path):
            self.main_window.log_message(
                f"Batch launching: {app.get('name', exe_path)}", 'info'
            )
            env_vars = self.config.get('environment_variables', {})
            success, _result = self.proton_manager.launch_program(
                runtime.get('path', ''),
                exe_path,
                app.get('run_directory', '') or os.path.dirname(exe_path),
                env_vars,
                self._startup_args(),
                output_callback=self.main_window.log_message,
                wine_options=self.more_options.get('wine_options', {}) or {},
                architecture=self.arch_combo.currentData(),
            )
            if not success:
                self.main_window.log_message(
                    f"{self.translator('launch_failed')}: {exe_path}", 'error'
                )
        elif not exe_path:
            self.main_window.log_message(
                f"Batch item has no executable: {app.get('name', '')}", 'warning'
            )

        interval = int(self.more_options.get('launch_interval', 0) or 0)
        if index + 1 < len(batch_apps):
            QTimer.singleShot(
                interval * 1000,
                lambda: self._batch_launch(batch_apps, index + 1)
            )

    # ------------------------------------------------------------------
    # Desktop file
    # ------------------------------------------------------------------
    def generate_desktop_file(self):
        """Open the desktop entry dialog and generate the .desktop file."""
        name = self.program_name.text().strip()
        exe_path = self.program_path.text().strip()

        if not name or not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('desktop_name_exe_required'),
            )
            return

        self._extract_icon_async(
            lambda icon_path, error: self._open_desktop_dialog(
                name, exe_path, icon_path, error
            )
        )

    def _prepare_shortcut_app(self, name, exe_path, icon_path):
        """Return the app used for recording plus a preview of the run config.

        Generating a shortcut always needs a saved application so the runner
        can attach launch time and total runtime to it.  Nothing is written
        until the shortcut dialog is accepted.
        """
        launch = self._get_app_config(icon_path=icon_path)
        app = self.config.find_app_by_exe(exe_path)
        if app is None:
            launch['name'] = self.config.unique_app_name(name)
            launch['description'] = name
            launch['tags'] = []
            ensure_app_prefix_fields(self.config, launch)
            return {
                'app': launch,
                'updates': None,
                'is_new': True,
                'preview': launch,
            }

        preview = dict(app)
        for key in self._shortcut_launch_fields():
            preview[key] = launch.get(key)
        ensure_app_prefix_fields(self.config, preview)
        return {
            'app': app,
            'updates': launch,
            'is_new': False,
            'preview': preview,
        }

    @staticmethod
    def _shortcut_launch_fields():
        return (
            'proton_path', 'runtime_type', 'exe_path', 'run_directory',
            'architecture', 'more_options',
        )

    def _commit_shortcut_app(self, app, updates, is_new):
        if is_new:
            self.config.save_app(app)
            message = self.translator('shortcut_app_saved').format(
                name=app.get('name', '')
            )
        else:
            for key in self._shortcut_launch_fields():
                app[key] = updates.get(key)
            ensure_app_prefix_fields(self.config, app)
            self.config._save_apps()
            message = self.translator('shortcut_app_updated').format(
                name=app.get('name', '')
            )
        self.main_window.log_message(message, 'info')
        saved_page = getattr(self.main_window, 'saved_page', None)
        if saved_page is not None:
            saved_page.refresh()

    def _open_desktop_dialog(self, name, exe_path, icon_path, error=''):
        if error:
            self.main_window.log_message(
                f"{self.translator('icon_extraction_failed')}: {error}", 'warning'
            )

        prepared = self._prepare_shortcut_app(name, exe_path, icon_path)
        pending = prepared['app']
        updates = prepared['updates']
        is_new = prepared['is_new']
        preview = prepared['preview']

        runtime = self.selected_runtime()
        prefix_type, prefix_path, _legacy = app_prefix_info(
            self.config, preview
        )
        wine_options = dict(self.more_options.get('wine_options', {}) or {})
        if prefix_type == 'wine' and not wine_options.get('prefix'):
            wine_options['prefix'] = prefix_path
        compat_data_path = prefix_path if prefix_type == 'proton' else ''

        options = {
            'name': name,
            'comment': name,
            'exe_path': exe_path,
            'working_dir': self.run_directory.text().strip(),
            'runtime_path': runtime.get('path', '') if runtime else '',
            'icon_path': icon_path,
            'args': self.more_options.get('startup_args', '') or '',
            'categories': 'Game;',
            'terminal': False,
            'target': 'desktop',
            'filename': sanitize_filename(name) + '.desktop',
            'app_id': preview.get('app_id', ''),
            'compat_data_path': compat_data_path,
        }

        dialog = DesktopEntryDialog(
            options,
            self.translator,
            runtimes=self.proton_manager.get_runtimes() if self.proton_manager else [],
            icon_extractor=self.icon_extractor,
            parent=self,
        )
        dialog.set_runtime_context(
            env_vars=self.config.get('environment_variables', {}),
            wine_options=wine_options,
            compat_data_path=compat_data_path,
        )

        if not dialog.exec():
            return

        self._commit_shortcut_app(pending, updates, is_new)
        desktop_options = dialog.get_options()
        success, result = self.desktop_generator.generate_desktop_file(
            **desktop_options,
            env_vars=self.config.get('environment_variables', {}),
            wine_options=wine_options,
            translator=self.translator,
        )

        if success:
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

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def refresh(self):
        """Refresh the page."""
        self.load_proton_versions()

        self.runtime_group.setTitle(self.translator('runtime_group'))
        self.program_group.setTitle(self.translator('program_path'))
        self.run_dir_group.setTitle(self.translator('run_directory'))
        self.name_group.setTitle(self.translator('program_name'))
        self.arch_group.setTitle(self.translator('architecture'))

        self.runtime_desc.setText(self.translator('runtime_desc'))
        self.program_desc.setText(self.translator('program_desc'))
        self.run_dir_desc.setText(self.translator('run_dir_desc'))
        self.name_desc.setText(self.translator('program_name_desc'))
        self.arch_desc.setText(self.translator('arch_desc'))
        self.runtime_hint.setText(self.translator('runtime_custom_hint'))

        self.runtime_table.setHorizontalHeaderLabels([
            self.translator('runtime_name'),
            self.translator('runtime_type'),
            self.translator('runtime_version'),
            self.translator('runtime_path'),
        ])
        self._refresh_runtime_type_column()

        self.info_32.setText(
            f"• {self.translator('arch_32')}: {self.translator('arch_32_desc')}"
        )
        self.info_64.setText(
            f"• {self.translator('arch_64')}: {self.translator('arch_64_desc')}"
        )
        self.info_auto.setText(
            f"• {self.translator('arch_auto')}: {self.translator('arch_auto_desc')}"
        )

        self.btn_browse_program.setText(self.translator('browse'))
        self.btn_browse_run_dir.setText(self.translator('browse'))
        self.btn_more_options.setText(self.translator('more_options'))
        self.btn_save_config.setText(self.translator('save_config'))
        self.btn_run.setText(self.translator('run'))
        self.btn_generate_desktop.setText(self.translator('generate_desktop'))
        self.btn_winetricks.setText(self.translator('open_winetricks'))
        self.btn_add_custom_runtime.setText(self.translator('add_custom_runtime'))
        self.btn_refresh_runtimes.setText(self.translator('refresh_runtimes'))
        self.btn_remove_runtime.setText(self.translator('remove_runtime'))

        self.program_name.setPlaceholderText(self.translator('program_name'))

        self._update_combo_item_text(self.arch_combo, {
            'auto': self.translator('arch_auto'),
            '32': self.translator('arch_32'),
            '64': self.translator('arch_64'),
        })

        proton_count = len([
            r for r in (self.proton_manager.get_runtimes() if self.proton_manager else [])
            if r.get('type') == 'proton'
        ])
        wine_count = len([
            r for r in (self.proton_manager.get_runtimes() if self.proton_manager else [])
            if r.get('type') == 'wine'
        ])
        if proton_count or wine_count:
            self.runtime_status.setText(
                self.translator('runtime_status_count').format(
                    proton=proton_count, wine=wine_count
                )
            )
        else:
            self.runtime_status.setText(self.translator('runtime_empty_hint'))

    def _refresh_runtime_type_column(self):
        for row in range(self.runtime_table.rowCount()):
            item = self.runtime_table.item(row, 0)
            if not item:
                continue
            runtime = item.data(Qt.ItemDataRole.UserRole)
            if runtime:
                self.runtime_table.item(row, 1).setText(
                    self.translator('runtime_type_' + runtime.get('type', 'proton'))
                )

    def _update_combo_item_text(self, combo, data_to_text):
        """Update display text for combobox items while preserving user data."""
        current_data = combo.currentData()
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data in data_to_text:
                combo.setItemText(i, data_to_text[data])
        if current_data is not None:
            index = combo.findData(current_data)
            if index >= 0:
                combo.setCurrentIndex(index)
