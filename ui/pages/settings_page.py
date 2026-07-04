# -*- coding: utf-8 -*-
"""
Settings page for Beer
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFileDialog, QGroupBox, QCheckBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QEvent


class NoWheelComboBox(QComboBox):
    """ComboBox that ignores scroll wheel events"""
    def wheelEvent(self, event):
        event.ignore()


class SettingsPage(QWidget):
    """Settings page widget"""
    
    def __init__(self, config, translator, main_window):
        super().__init__()
        self.config = config
        self.translator = translator
        self.main_window = main_window
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Tab widget for general and advanced settings
        self.tabs = QTabWidget()
        
        # General settings tab
        self.general_tab = self._create_general_tab()
        self.tabs.addTab(self.general_tab, self.translator('general_settings'))
        
        # Advanced settings tab
        self.advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(self.advanced_tab, self.translator('advanced_settings'))
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_reset = QPushButton(self.translator('reset'))
        self.btn_reset.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.btn_reset)
        
        # Save button removed - settings auto-save
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self):
        """Create general settings tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Custom Proton path
        custom_proton_group = QGroupBox(self.translator('custom_proton_path'))
        custom_proton_layout = QVBoxLayout(custom_proton_group)
        
        custom_proton_desc = QLabel(self.translator('custom_proton_desc'))
        custom_proton_desc.setWordWrap(True)
        custom_proton_desc.setStyleSheet("color: gray; font-size: 11px;")
        custom_proton_layout.addWidget(custom_proton_desc)
        
        custom_proton_row = QHBoxLayout()
        self.chk_custom_proton = QCheckBox()
        self.chk_custom_proton.toggled.connect(self.on_custom_proton_toggled)
        custom_proton_row.addWidget(self.chk_custom_proton)
        
        self.txt_custom_proton_path = QLineEdit()
        self.txt_custom_proton_path.setPlaceholderText("/path/to/custom/proton")
        self.txt_custom_proton_path.editingFinished.connect(self.on_custom_proton_path_changed)
        custom_proton_row.addWidget(self.txt_custom_proton_path)
        
        self.btn_browse_custom_proton = QPushButton(self.translator('browse'))
        self.btn_browse_custom_proton.clicked.connect(self.browse_custom_proton)
        custom_proton_row.addWidget(self.btn_browse_custom_proton)
        
        custom_proton_layout.addLayout(custom_proton_row)
        layout.addWidget(custom_proton_group)
        
        # Proton search paths
        proton_paths_group = QGroupBox(self.translator('proton_search_paths'))
        proton_paths_layout = QVBoxLayout(proton_paths_group)
        
        proton_paths_desc = QLabel(self.translator('proton_paths_desc'))
        proton_paths_desc.setWordWrap(True)
        proton_paths_desc.setStyleSheet("color: gray; font-size: 11px;")
        proton_paths_layout.addWidget(proton_paths_desc)
        
        self.txt_proton_paths = QLineEdit()
        self.txt_proton_paths.setPlaceholderText("/path/1;/path/2;/path/3")
        self.txt_proton_paths.editingFinished.connect(self.on_proton_paths_changed)
        proton_paths_layout.addWidget(self.txt_proton_paths)
        
        layout.addWidget(proton_paths_group)
        
        # Default page
        default_page_group = QGroupBox(self.translator('default_page'))
        default_page_layout = QVBoxLayout(default_page_group)
        
        default_page_desc = QLabel(self.translator('default_page_desc'))
        default_page_desc.setWordWrap(True)
        default_page_desc.setStyleSheet("color: gray; font-size: 11px;")
        default_page_layout.addWidget(default_page_desc)
        
        self.combo_default_page = NoWheelComboBox()
        self.combo_default_page.addItem(self.translator('main_page'), 'main')
        self.combo_default_page.addItem(self.translator('saved_apps'), 'saved')
        self.combo_default_page.addItem(self.translator('log'), 'log')
        self.combo_default_page.addItem(self.translator('settings'), 'settings')
        self.combo_default_page.currentIndexChanged.connect(self.on_default_page_changed)
        self.combo_default_page.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        default_page_layout.addWidget(self.combo_default_page)
        
        layout.addWidget(default_page_group)
        
        # Theme
        theme_group = QGroupBox(self.translator('theme'))
        theme_layout = QVBoxLayout(theme_group)
        
        theme_desc = QLabel(self.translator('theme_desc'))
        theme_desc.setWordWrap(True)
        theme_desc.setStyleSheet("color: gray; font-size: 11px;")
        theme_layout.addWidget(theme_desc)
        
        self.combo_theme = NoWheelComboBox()
        self.combo_theme.addItem(self.translator('theme_system'), 'system')
        self.combo_theme.addItem(self.translator('theme_light'), 'light')
        self.combo_theme.addItem(self.translator('theme_dark'), 'dark')
        self.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        self.combo_theme.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        theme_layout.addWidget(self.combo_theme)
        
        layout.addWidget(theme_group)
        
        # Language
        language_group = QGroupBox(self.translator('language'))
        language_layout = QVBoxLayout(language_group)
        
        language_desc = QLabel(self.translator('language_desc'))
        language_desc.setWordWrap(True)
        language_desc.setStyleSheet("color: gray; font-size: 11px;")
        language_layout.addWidget(language_desc)
        
        self.combo_language = NoWheelComboBox()
        self.combo_language.addItem(self.translator('language_system'), 'system')
        self.combo_language.addItem("English", 'en')
        self.combo_language.addItem("中文", 'zh')
        self.combo_language.currentIndexChanged.connect(self.on_language_changed)
        self.combo_language.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        language_layout.addWidget(self.combo_language)
        
        layout.addWidget(language_group)
        
        # Show log on start
        log_group = QGroupBox(self.translator('show_log_on_start'))
        log_layout = QVBoxLayout(log_group)
        
        log_desc = QLabel(self.translator('show_log_desc'))
        log_desc.setWordWrap(True)
        log_desc.setStyleSheet("color: gray; font-size: 11px;")
        log_layout.addWidget(log_desc)
        
        self.chk_show_log = QCheckBox()
        self.chk_show_log.toggled.connect(self.on_show_log_changed)
        log_layout.addWidget(self.chk_show_log)
        
        layout.addWidget(log_group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_advanced_tab(self):
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Environment variables
        env_group = QGroupBox(self.translator('environment_variables'))
        env_layout = QVBoxLayout(env_group)
        
        env_desc = QLabel(self.translator('env_vars_desc'))
        env_desc.setWordWrap(True)
        env_desc.setStyleSheet("color: gray; font-size: 11px;")
        env_layout.addWidget(env_desc)
        
        # Table for environment variables
        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels([
            self.translator('variable'),
            self.translator('value')
        ])
        self.env_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.env_table.setMinimumHeight(200)
        self.env_table.cellChanged.connect(self.on_env_table_changed)
        env_layout.addWidget(self.env_table)
        
        # Buttons for table
        env_button_layout = QHBoxLayout()
        
        self.btn_add_env = QPushButton(self.translator('add'))
        self.btn_add_env.clicked.connect(self.add_env_variable)
        env_button_layout.addWidget(self.btn_add_env)
        
        self.btn_remove_env = QPushButton(self.translator('remove'))
        self.btn_remove_env.clicked.connect(self.remove_env_variable)
        env_button_layout.addWidget(self.btn_remove_env)
        
        env_button_layout.addStretch()
        env_layout.addLayout(env_button_layout)
        
        layout.addWidget(env_group)
        layout.addStretch()
        
        return widget
    
    def load_settings(self):
        """Load settings from config"""
        # Custom Proton
        self.chk_custom_proton.setChecked(self.config.get('custom_proton_enabled', False))
        self.txt_custom_proton_path.setText(self.config.get('custom_proton_path', ''))
        
        # Proton search paths
        paths = self.config.get('proton_search_paths', [])
        self.txt_proton_paths.setText(';'.join(paths))
        
        # Default page
        default_page = self.config.get('default_page', 'main')
        index = self.combo_default_page.findData(default_page)
        if index >= 0:
            self.combo_default_page.setCurrentIndex(index)
        
        # Theme
        theme = self.config.get('theme', 'system')
        index = self.combo_theme.findData(theme)
        if index >= 0:
            self.combo_theme.setCurrentIndex(index)
        
        # Language
        language = self.config.get('language', 'system')
        index = self.combo_language.findData(language)
        if index >= 0:
            self.combo_language.setCurrentIndex(index)
        
        # Environment variables
        env_vars = self.config.get('environment_variables', {})
        self.env_table.setRowCount(0)
        for key, value in env_vars.items():
            self.add_env_variable(key, value)
    
    def save_settings(self):
        """Save settings to config"""
        # Custom Proton
        self.config.set('custom_proton_enabled', self.chk_custom_proton.isChecked())
        self.config.set('custom_proton_path', self.txt_custom_proton_path.text())
        
        # Tool directory
        self.config.set('tool_directory', self.txt_tool_directory.text())
        
        # Proton search paths
        paths_text = self.txt_proton_paths.text()
        paths = [p.strip() for p in paths_text.split(';') if p.strip()]
        self.config.set('proton_search_paths', paths)
        
        # Default page
        self.config.set('default_page', self.combo_default_page.currentData())
        
        # Theme
        self.config.set('theme', self.combo_theme.currentData())
        
        # Language
        self.config.set('language', self.combo_language.currentData())
        
        # Environment variables
        env_vars = {}
        for row in range(self.env_table.rowCount()):
            key_item = self.env_table.item(row, 0)
            value_item = self.env_table.item(row, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    env_vars[key] = value
        self.config.set('environment_variables', env_vars)
        
        # Refresh UI
        self.main_window.refresh_ui()
        
        QMessageBox.information(
            self,
            self.translator('success'),
            self.translator('settings_saved')
        )
    
    def reset_settings(self):
        """Reset settings to default"""
        reply = QMessageBox.question(
            self,
            self.translator('warning'),
            self.translator('confirm_reset_msg'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.reset_to_default()
            self.load_settings()
            self.main_window.refresh_ui()
            
            QMessageBox.information(
                self,
                self.translator('success'),
                self.translator('config_reset')
            )
    
    def on_custom_proton_toggled(self, checked):
        """Handle custom Proton toggle - save immediately"""
        self.txt_custom_proton_path.setEnabled(checked)
        self.btn_browse_custom_proton.setEnabled(checked)
        self.config.set('custom_proton_enabled', checked)
        self.main_window.refresh_ui()
    
    def on_custom_proton_path_changed(self):
        """Handle custom Proton path change - save immediately"""
        self.config.set('custom_proton_path', self.txt_custom_proton_path.text())
        self.main_window.refresh_ui()
    
    def on_proton_paths_changed(self):
        """Handle proton paths change - save immediately"""
        paths_text = self.txt_proton_paths.text()
        paths = [p.strip() for p in paths_text.split(';') if p.strip()]
        self.config.set('proton_search_paths', paths)
        self.main_window.refresh_ui()
    
    def on_show_log_changed(self, checked):
        """Handle show log change - save immediately"""
        self.config.set('show_log_on_start', checked)

    def on_default_page_changed(self, index):
        """Handle default page change - save immediately"""
        if index >= 0:
            self.config.set('default_page', self.combo_default_page.currentData())

    def on_theme_changed(self, index):
        """Handle theme change - apply immediately"""
        if index >= 0:
            self.config.set('theme', self.combo_theme.currentData())
            self.main_window.apply_theme()

    def on_language_changed(self, index):
        """Handle language change - apply immediately"""
        if index >= 0:
            self.config.set('language', self.combo_language.currentData())
            self.main_window.refresh_ui()
    
    def on_env_table_changed(self, row, column):
        """Handle environment table change - save immediately"""
        env_vars = {}
        for r in range(self.env_table.rowCount()):
            key_item = self.env_table.item(r, 0)
            value_item = self.env_table.item(r, 1)
            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()
                if key:
                    env_vars[key] = value
        self.config.set('environment_variables', env_vars)

    def toggle_custom_proton(self, checked):
        """Toggle custom Proton path"""
        self.txt_custom_proton_path.setEnabled(checked)
        self.btn_browse_custom_proton.setEnabled(checked)
    
    def browse_custom_proton(self):
        """Browse for custom Proton directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('select_proton')
        )
        
        if directory:
            self.txt_custom_proton_path.setText(directory)
            self.config.set('custom_proton_path', directory)
            self.main_window.refresh_ui()
    
    def add_env_variable(self, key='', value=''):
        """Add environment variable to table"""
        row = self.env_table.rowCount()
        self.env_table.insertRow(row)
        self.env_table.setItem(row, 0, QTableWidgetItem(key))
        self.env_table.setItem(row, 1, QTableWidgetItem(value))
        # Trigger save
        self.on_env_table_changed(row, 0)
    
    def remove_env_variable(self):
        """Remove selected environment variable"""
        current_row = self.env_table.currentRow()
        if current_row >= 0:
            self.env_table.removeRow(current_row)
            # Trigger save
            env_vars = {}
            for r in range(self.env_table.rowCount()):
                key_item = self.env_table.item(r, 0)
                value_item = self.env_table.item(r, 1)
                if key_item and value_item:
                    key = key_item.text().strip()
                    value = value_item.text().strip()
                    if key:
                        env_vars[key] = value
            self.config.set('environment_variables', env_vars)
    
    def refresh(self):
        """Refresh the page"""
        # Update tab titles
        self.tabs.setTabText(0, self.translator('general_settings'))
        self.tabs.setTabText(1, self.translator('advanced_settings'))
        
        # Update button texts
        self.btn_reset.setText(self.translator('reset'))
        self.btn_add_env.setText(self.translator('add'))
        self.btn_remove_env.setText(self.translator('remove'))
