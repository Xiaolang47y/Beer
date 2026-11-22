# -*- coding: utf-8 -*-
"""
Winetricks component manager dialog for Beer.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QPlainTextEdit, QMessageBox, QFileDialog,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment
from PyQt6.QtGui import QFont

from core.runtime_utils import detect_runtime, expand_path
from core.winetricks_manager import (
    WinetricksManager,
    get_items,
    item_text,
    prefix_for_name,
)
from ui.widgets import BeerComboBox


class WinetricksDialog(QDialog):
    """Dialog to select Winetricks components and install them."""

    def __init__(self, translator, runtimes=None, config=None, parent=None,
                 app_name='', runtime_path='', prefix=''):
        super().__init__(parent)
        self.translator = translator
        self.runtimes = runtimes or []
        self.config = config
        self.manager = WinetricksManager(config)
        self.process = None
        self._items = []

        self.setWindowTitle(self.translator('winetricks_title'))
        self.setMinimumSize(900, 680)

        self.init_ui()
        self.load_items(include_unknown=True)
        self.load_runtimes(runtime_path)
        self.init_prefix(app_name, prefix)
        self.update_winetricks_buttons()

        # First run with Winetricks available: discover components once and
        # persist them, so descriptions survive a restart.
        if self.manager.find_winetricks() and not self.manager.cached_items():
            self.manager.refresh_discovered_items()
            self.load_items(include_unknown=True)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(self.translator('winetricks_title'))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        warning = QLabel(self.translator('winetricks_network_warning'))
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "color: #ff9800; font-size: 11px;"
            " border: 1px solid #ff9800; border-radius: 4px; padding: 8px;"
        )
        layout.addWidget(warning)

        # Target runtime and prefix
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(self.translator('winetricks_runtime')))
        self.combo_runtime = BeerComboBox()
        self.combo_runtime.setMinimumWidth(260)
        top_row.addWidget(self.combo_runtime)

        top_row.addWidget(QLabel(self.translator('winetricks_prefix')))
        self.txt_prefix = QLineEdit()
        top_row.addWidget(self.txt_prefix)
        self.btn_browse_prefix = QPushButton(self.translator('browse'))
        self.btn_browse_prefix.clicked.connect(self.browse_prefix)
        top_row.addWidget(self.btn_browse_prefix)
        layout.addLayout(top_row)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(self.translator('search')))
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText(self.translator('winetricks_filter_placeholder'))
        self.txt_filter.textChanged.connect(self.filter_items)
        filter_row.addWidget(self.txt_filter)

        self.btn_select_all = QPushButton(self.translator('winetricks_select_all'))
        self.btn_select_all.clicked.connect(lambda: self.set_all_checked(True))
        filter_row.addWidget(self.btn_select_all)

        self.btn_clear_selection = QPushButton(self.translator('winetricks_clear_selection'))
        self.btn_clear_selection.clicked.connect(lambda: self.set_all_checked(False))
        filter_row.addWidget(self.btn_clear_selection)

        self.btn_refresh_list = QPushButton(self.translator('winetricks_refresh_list'))
        self.btn_refresh_list.clicked.connect(self.refresh_items)
        filter_row.addWidget(self.btn_refresh_list)
        layout.addLayout(filter_row)

        # Component table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            self.translator('winetricks_select'),
            self.translator('winetricks_component'),
            self.translator('winetricks_category'),
            self.translator('winetricks_description'),
            self.translator('winetricks_network_column'),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        # Buttons
        button_row = QHBoxLayout()
        self.btn_download_winetricks = QPushButton(self.translator('winetricks_download'))
        self.btn_download_winetricks.clicked.connect(self.download_winetricks)
        button_row.addWidget(self.btn_download_winetricks)

        self.btn_install = QPushButton(self.translator('winetricks_install_selected'))
        self.btn_install.setStyleSheet(
            "background-color: #4a86c8; color: white; font-weight: bold;"
        )
        self.btn_install.clicked.connect(self.install_selected)
        button_row.addWidget(self.btn_install)

        button_row.addStretch()

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            self.translator('close')
        )
        close_buttons.rejected.connect(self.reject)
        button_row.addWidget(close_buttons)
        layout.addLayout(button_row)

        log_label = QLabel(self.translator('winetricks_output'))
        log_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(log_label)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        font = QFont('Monospace')
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.log_output.setFont(font)
        self.log_output.setMaximumHeight(150)
        layout.addWidget(self.log_output)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def language(self):
        return getattr(self.translator, 'resolved_language', 'en')

    def load_items(self, include_unknown=False):
        self._items = get_items(
            self.language(), include_unknown=include_unknown, manager=self.manager
        )
        self.table.setRowCount(0)
        for item in self._items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            check_item = QTableWidgetItem('')
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            check_item.setCheckState(Qt.CheckState.Unchecked)
            check_item.setData(Qt.ItemDataRole.UserRole, item['verb'])
            self.table.setItem(row, 0, check_item)

            self.table.setItem(row, 1, QTableWidgetItem(item_text(item, 'name', self.language())))
            self.table.setItem(row, 2, QTableWidgetItem(item_text(item, 'category', self.language())))
            self.table.setItem(row, 3, QTableWidgetItem(item_text(item, 'description', self.language())))

            flags = []
            if item.get('network'):
                flags.append(self.translator('winetricks_network_short'))
            if item.get('large'):
                flags.append(self.translator('winetricks_large_short'))
            self.table.setItem(row, 4, QTableWidgetItem(' / '.join(flags) or '-'))

    def filter_items(self, text):
        text = (text or '').lower()
        for row in range(self.table.rowCount()):
            haystack = ' '.join(
                self.table.item(row, column).text().lower()
                for column in (1, 2, 3)
                if self.table.item(row, column)
            )
            self.table.setRowHidden(row, bool(text) and text not in haystack)

    def refresh_items(self):
        self.log(self.translator('winetricks_refreshing'), 'info')
        has_tool = bool(self.manager.find_winetricks())
        if has_tool:
            self.manager.refresh_discovered_items()
        self.load_items(include_unknown=True)
        if has_tool:
            self.log(self.translator('winetricks_list_updated'), 'success')
        else:
            self.log(self.translator('winetricks_builtin_only'), 'warning')

    def load_runtimes(self, selected_path=''):
        self.combo_runtime.clear()
        for runtime in self.runtimes:
            label = '{} · {} ({})'.format(
                runtime.get('name', ''),
                runtime.get('version_str', ''),
                self.translator('runtime_type_' + runtime.get('type', 'proton'))
            )
            self.combo_runtime.addItem(label, runtime.get('path', ''))
        if self.combo_runtime.count() == 0:
            self.combo_runtime.addItem(self.translator('no_runtimes'), '')
        if selected_path:
            index = self.combo_runtime.findData(selected_path)
            if index >= 0:
                self.combo_runtime.setCurrentIndex(index)

    def init_prefix(self, app_name='', prefix=''):
        if prefix:
            self.txt_prefix.setText(prefix)
            return
        default = prefix_for_name(self.config, app_name or 'default')
        self.txt_prefix.setText(default)

    def update_winetricks_buttons(self):
        found = bool(self.manager.find_winetricks())
        self.btn_download_winetricks.setVisible(not found)
        if found:
            self.log(f'Using Winetricks: {self.manager.find_winetricks()}', 'success')
        else:
            self.log(self.translator('winetricks_not_found'), 'warning')

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def set_all_checked(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)

    def selected_verbs(self):
        verbs = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                verb = item.data(Qt.ItemDataRole.UserRole)
                if verb:
                    verbs.append(verb)
        return verbs

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def browse_prefix(self):
        directory = QFileDialog.getExistingDirectory(
            self, self.translator('winetricks_prefix'), self.txt_prefix.text()
        )
        if directory:
            self.txt_prefix.setText(directory)

    def download_winetricks(self):
        self.btn_download_winetricks.setEnabled(False)
        self.log(self.translator('winetricks_downloading'), 'info')
        path, error = self.manager.download_winetricks(
            progress_callback=lambda message, level: self.log(message, level)
        )
        self.btn_download_winetricks.setEnabled(True)
        if path:
            self.update_winetricks_buttons()
            self.refresh_items()
        else:
            QMessageBox.warning(self, self.translator('error'), error)

    def install_selected(self):
        if self.process is not None:
            QMessageBox.information(
                self, self.translator('info'),
                self.translator('winetricks_running')
            )
            return

        verbs = self.selected_verbs()
        if not verbs:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('winetricks_no_selection')
            )
            return

        prefix = self.txt_prefix.text().strip()
        if not prefix:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('winetricks_prefix_required')
            )
            return
        prefix = expand_path(prefix)

        runtime_path = self.combo_runtime.currentData() or ''
        runtime = detect_runtime(runtime_path) if runtime_path else None
        if runtime is None:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('runtime_select_first')
            )
            return

        if not self.manager.find_winetricks():
            reply = QMessageBox.question(
                self, self.translator('warning'),
                self.translator('winetricks_download_prompt'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.download_winetricks()
            return

        argv, env = self.manager.build_command(runtime, verbs, prefix=prefix)
        if not argv:
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('winetricks_not_found')
            )
            return

        self.log(
            f"Running: {' '.join(argv)}\nWINEPREFIX={prefix}",
            'info'
        )
        self.log(self.translator('winetricks_install_started'), 'info')

        proc_env = QProcessEnvironment.systemEnvironment()
        for key, value in (env or {}).items():
            proc_env.insert(str(key), str(value))

        self.process = QProcess(self)
        self.process.setProcessEnvironment(proc_env)
        self.process.setWorkingDirectory(os.path.dirname(prefix) if prefix else os.path.expanduser('~'))
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self.on_process_finished)
        self.process.start(argv[0], argv[1:])
        if not self.process.waitForStarted(5000):
            self.log('Failed to start Winetricks.', 'error')
            self.process = None
            return

        self.btn_install.setEnabled(False)
        self.btn_download_winetricks.setEnabled(False)
        self.table.setEnabled(False)

    def read_stdout(self):
        if not self.process:
            return
        text = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.log(text, 'normal')

    def read_stderr(self):
        if not self.process:
            return
        text = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace')
        self.log(text, 'error')

    def on_process_finished(self, exit_code, _status):
        self.log(
            self.translator('winetricks_install_done') if exit_code == 0
            else self.translator('winetricks_install_failed'),
            'success' if exit_code == 0 else 'error'
        )
        self.process = None
        self.btn_install.setEnabled(True)
        self.btn_download_winetricks.setEnabled(True)
        self.table.setEnabled(True)

    def log(self, message, level='normal'):
        if not message:
            return
        self.log_output.appendPlainText(str(message).rstrip('\n'))
        if level == 'error':
            self.log_output.appendPlainText('')
