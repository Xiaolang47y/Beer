# -*- coding: utf-8 -*-
"""
More options dialog for Beer
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QFileDialog, QGroupBox, QSpinBox,
    QListWidget, QListWidgetItem, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class MoreOptionsDialog(QDialog):
    """More options dialog"""
    
    def __init__(self, options, translator, parent=None):
        super().__init__(parent)
        self.options = options.copy()
        self.translator = translator
        
        self.setWindowTitle(self.translator('more_options'))
        self.setMinimumSize(600, 500)
        
        self.init_ui()
        self.load_options()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        
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
        
        # Batch launch
        batch_group = QGroupBox(self.translator('batch_launch'))
        batch_layout = QVBoxLayout(batch_group)
        
        batch_desc = QLabel(self.translator('batch_launch_desc'))
        batch_desc.setWordWrap(True)
        batch_desc.setStyleSheet("color: gray; font-size: 11px;")
        batch_layout.addWidget(batch_desc)
        
        # Interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel(self.translator('launch_interval'))
        interval_layout.addWidget(interval_label)
        
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(0, 60)
        self.spin_interval.setValue(0)
        self.spin_interval.setSuffix(" s")
        interval_layout.addWidget(self.spin_interval)
        interval_layout.addStretch()
        
        batch_layout.addLayout(interval_layout)
        
        # Batch apps list
        self.list_batch_apps = QListWidget()
        self.list_batch_apps.setMaximumHeight(150)
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
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_options(self):
        """Load options from dict"""
        self.txt_startup_args.setText(self.options.get('startup_args', ''))
        self.spin_interval.setValue(self.options.get('launch_interval', 0))
        self.txt_pre_launch_script.setText(self.options.get('pre_launch_script', ''))
        
        # Load batch apps
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
        
        return {
            'startup_args': self.txt_startup_args.text(),
            'launch_interval': self.spin_interval.value(),
            'pre_launch_script': self.txt_pre_launch_script.text(),
            'batch_apps': batch_apps
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
            import os
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
