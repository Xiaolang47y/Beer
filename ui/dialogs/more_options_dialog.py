# -*- coding: utf-8 -*-
"""
More options dialog for Beer
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QGroupBox, QSpinBox,
    QListWidget, QListWidgetItem, QDialogButtonBox,
    QCheckBox, QScrollArea, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt
from ui.widgets import BeerComboBox


class MoreOptionsDialog(QDialog):
    """More options dialog"""

    def __init__(self, options, translator, parent=None):
        super().__init__(parent)
        self.options = dict(options or {})
        self.translator = translator

        self.setWindowTitle(self.translator('more_options'))
        self.resize(820, 700)
        self.setMinimumSize(700, 520)

        self.init_ui()
        self.load_options()

    def init_ui(self):
        """Initialize UI"""
        outer_layout = QVBoxLayout(self)

        # Keep the dialog usable on small screens: the content scrolls instead
        # of squeezing rows into each other.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

        # Startup arguments
        args_group = QGroupBox(self.translator('startup_options'))
        args_layout = QVBoxLayout(args_group)

        args_desc = QLabel(self.translator('startup_args_desc'))
        args_desc.setWordWrap(True)
        args_desc.setStyleSheet("color: gray; font-size: 11px;")
        args_layout.addWidget(args_desc)

        self.txt_startup_args = QLineEdit()
        self.txt_startup_args.setPlaceholderText("-windowed -width 1920 -height 1080")
        args_layout.addWidget(self.txt_startup_args)

        layout.addWidget(args_group)

        # Wine parameters
        wine_group = QGroupBox(self.translator('wine_options'))
        wine_layout = QVBoxLayout(wine_group)

        wine_desc = QLabel(self.translator('wine_options_desc'))
        wine_desc.setWordWrap(True)
        wine_desc.setStyleSheet("color: gray; font-size: 11px;")
        wine_layout.addWidget(wine_desc)

        # Two balanced columns keep the Wine options readable and avoid rows
        # overlapping when the dialog is shown on a small screen.
        columns = QHBoxLayout()
        columns.setSpacing(18)

        left_column = QVBoxLayout()
        left_column.setSpacing(5)

        left_column.addWidget(QLabel(self.translator('wine_prefix')))
        prefix_row = QHBoxLayout()
        self.txt_wine_prefix = QLineEdit()
        self.txt_wine_prefix.setPlaceholderText(
            self.translator('wine_prefix_placeholder')
        )
        self.txt_wine_prefix.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        prefix_row.addWidget(self.txt_wine_prefix, 1)
        self.btn_browse_prefix = QPushButton(self.translator('browse'))
        self.btn_browse_prefix.clicked.connect(self.browse_wine_prefix)
        prefix_row.addWidget(self.btn_browse_prefix)
        left_column.addLayout(prefix_row)

        left_column.addWidget(QLabel(self.translator('wine_windows_version')))
        self.combo_windows_version = BeerComboBox()
        self.combo_windows_version.addItem(self.translator('wine_default'), 'default')
        self.combo_windows_version.addItem('Windows 7', 'win7')
        self.combo_windows_version.addItem('Windows 8', 'win8')
        self.combo_windows_version.addItem('Windows 10', 'win10')
        self.combo_windows_version.addItem('Windows 11', 'win11')
        self.combo_windows_version.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        left_column.addWidget(self.combo_windows_version)

        left_column.addWidget(QLabel(self.translator('wine_debug')))
        self.combo_wine_debug = BeerComboBox()
        self.combo_wine_debug.addItem(self.translator('wine_debug_default'), '')
        self.combo_wine_debug.addItem(self.translator('wine_debug_none'), 'none')
        self.combo_wine_debug.addItem(self.translator('wine_debug_err'), 'err')
        self.combo_wine_debug.addItem(self.translator('wine_debug_warn'), 'warn')
        self.combo_wine_debug.addItem(self.translator('wine_debug_fixme'), 'fixme')
        self.combo_wine_debug.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        left_column.addWidget(self.combo_wine_debug)

        sync_row = QHBoxLayout()
        self.chk_esync = QCheckBox(self.translator('wine_esync'))
        self.chk_fsync = QCheckBox(self.translator('wine_fsync'))
        sync_row.addWidget(self.chk_esync)
        sync_row.addWidget(self.chk_fsync)
        sync_row.addStretch()
        left_column.addLayout(sync_row)
        left_column.addStretch()

        right_column = QVBoxLayout()
        right_column.setSpacing(5)

        right_column.addWidget(QLabel(self.translator('wine_dll_overrides')))
        self.txt_dll_overrides = QLineEdit()
        self.txt_dll_overrides.setPlaceholderText("d3d11=n,b;dxgi=n,b")
        self.txt_dll_overrides.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        right_column.addWidget(self.txt_dll_overrides)

        dll_desc = QLabel(self.translator('wine_dll_overrides_desc'))
        dll_desc.setWordWrap(True)
        dll_desc.setStyleSheet("color: gray; font-size: 10px;")
        right_column.addWidget(dll_desc)

        self.chk_wined3d = QCheckBox(self.translator('wine_use_wined3d'))
        right_column.addWidget(self.chk_wined3d)

        right_column.addWidget(QLabel(self.translator('wine_extra_args')))
        self.txt_wine_extra_args = QLineEdit()
        self.txt_wine_extra_args.setPlaceholderText("-d3d9.exe=... (Wine only)")
        self.txt_wine_extra_args.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        right_column.addWidget(self.txt_wine_extra_args)

        extra_desc = QLabel(self.translator('wine_extra_args_desc'))
        extra_desc.setWordWrap(True)
        extra_desc.setStyleSheet("color: gray; font-size: 10px;")
        right_column.addWidget(extra_desc)
        right_column.addStretch()

        columns.addLayout(left_column, 1)
        columns.addLayout(right_column, 1)
        wine_layout.addLayout(columns)

        layout.addWidget(wine_group)

        # Batch launch
        batch_group = QGroupBox(self.translator('batch_launch'))
        batch_layout = QVBoxLayout(batch_group)

        batch_desc = QLabel(self.translator('batch_launch_desc'))
        batch_desc.setWordWrap(True)
        batch_desc.setStyleSheet("color: gray; font-size: 11px;")
        batch_layout.addWidget(batch_desc)

        interval_layout = QHBoxLayout()
        interval_label = QLabel(self.translator('launch_interval'))
        interval_layout.addWidget(interval_label)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(0, 600)
        self.spin_interval.setValue(0)
        self.spin_interval.setSuffix(" s")
        interval_layout.addWidget(self.spin_interval)
        interval_layout.addStretch()

        batch_layout.addLayout(interval_layout)

        self.list_batch_apps = QListWidget()
        self.list_batch_apps.setMaximumHeight(130)
        self.list_batch_apps.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        batch_layout.addWidget(self.list_batch_apps)

        batch_button_layout = QHBoxLayout()

        self.btn_add_batch = QPushButton(self.translator('add'))
        self.btn_add_batch.clicked.connect(self.add_batch_app)
        batch_button_layout.addWidget(self.btn_add_batch)

        self.btn_remove_batch = QPushButton(self.translator('remove'))
        self.btn_remove_batch.clicked.connect(self.remove_batch_app)
        batch_button_layout.addWidget(self.btn_remove_batch)

        batch_button_layout.addStretch()
        batch_layout.addLayout(batch_button_layout)

        reorder_label = QLabel(self.translator('drag_to_reorder'))
        reorder_label.setStyleSheet("color: gray; font-size: 10px;")
        batch_layout.addWidget(reorder_label)

        layout.addWidget(batch_group)

        # Command script
        script_group = QGroupBox(self.translator('command_script'))
        script_layout = QVBoxLayout(script_group)

        script_desc = QLabel(self.translator('pre_launch_desc'))
        script_desc.setWordWrap(True)
        script_desc.setStyleSheet("color: gray; font-size: 11px;")
        script_layout.addWidget(script_desc)

        script_row = QHBoxLayout()
        self.txt_pre_launch_script = QLineEdit()
        self.txt_pre_launch_script.setPlaceholderText("/path/to/script.sh")
        script_row.addWidget(self.txt_pre_launch_script)

        self.btn_browse_script = QPushButton(self.translator('browse'))
        self.btn_browse_script.clicked.connect(self.browse_script)
        script_row.addWidget(self.btn_browse_script)

        script_layout.addLayout(script_row)

        layout.addWidget(script_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            self.translator('ok')
        )
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            self.translator('cancel')
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        outer_layout.addWidget(button_box)

    def load_options(self):
        """Load options from dict"""
        self.txt_startup_args.setText(self.options.get('startup_args', ''))
        self.spin_interval.setValue(self.options.get('launch_interval', 0))
        self.txt_pre_launch_script.setText(self.options.get('pre_launch_script', ''))

        wine_options = self.options.get('wine_options', {}) or {}
        self.txt_wine_prefix.setText(wine_options.get('prefix', ''))
        index = self.combo_windows_version.findData(
            wine_options.get('windows_version', 'default')
        )
        if index >= 0:
            self.combo_windows_version.setCurrentIndex(index)
        self.txt_dll_overrides.setText(wine_options.get('dll_overrides', ''))
        index = self.combo_wine_debug.findData(wine_options.get('debug', ''))
        if index >= 0:
            self.combo_wine_debug.setCurrentIndex(index)
        self.chk_esync.setChecked(bool(wine_options.get('esync', False)))
        self.chk_fsync.setChecked(bool(wine_options.get('fsync', False)))
        self.chk_wined3d.setChecked(bool(wine_options.get('use_wined3d', False)))
        self.txt_wine_extra_args.setText(wine_options.get('extra_args', ''))

        batch_apps = self.options.get('batch_apps', [])
        for app in batch_apps:
            item = QListWidgetItem(app.get('name', 'Unknown'))
            item.setData(Qt.ItemDataRole.UserRole, app)
            self.list_batch_apps.addItem(item)

    def get_options(self):
        """Get options as dict"""
        batch_apps = []
        for i in range(self.list_batch_apps.count()):
            item = self.list_batch_apps.item(i)
            app = item.data(Qt.ItemDataRole.UserRole)
            if app:
                batch_apps.append(app)

        wine_options = {
            'prefix': self.txt_wine_prefix.text().strip(),
            'windows_version': self.combo_windows_version.currentData() or 'default',
            'dll_overrides': self.txt_dll_overrides.text().strip(),
            'debug': self.combo_wine_debug.currentData() or '',
            'esync': self.chk_esync.isChecked(),
            'fsync': self.chk_fsync.isChecked(),
            'use_wined3d': self.chk_wined3d.isChecked(),
            'extra_args': self.txt_wine_extra_args.text().strip(),
        }

        return {
            'startup_args': self.txt_startup_args.text(),
            'launch_interval': self.spin_interval.value(),
            'pre_launch_script': self.txt_pre_launch_script.text(),
            'wine_options': wine_options,
            'batch_apps': batch_apps,
        }

    def add_batch_app(self):
        """Add application to batch launch list"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('select_exe'),
            "",
            f"{self.translator('exe_files')} (*.exe);;{self.translator('all_files')} (*)"
        )

        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            app = {
                'name': name,
                'exe_path': file_path,
                'run_directory': os.path.dirname(file_path)
            }

            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, app)
            self.list_batch_apps.addItem(item)

    def remove_batch_app(self):
        """Remove selected application from batch list"""
        current_row = self.list_batch_apps.currentRow()
        if current_row >= 0:
            self.list_batch_apps.takeItem(current_row)

    def browse_script(self):
        """Browse for script file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('select_script'),
            "",
            "Shell Scripts (*.sh);;All Files (*)"
        )

        if file_path:
            self.txt_pre_launch_script.setText(file_path)

    def browse_wine_prefix(self):
        """Browse for Wine prefix directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('wine_prefix'),
            self.txt_wine_prefix.text() or ''
        )
        if directory:
            self.txt_wine_prefix.setText(directory)
