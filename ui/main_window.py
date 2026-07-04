# -*- coding: utf-8 -*-
"""
Main window for Beer
"""

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar
)
from PyQt6.QtCore import Qt

from ui.pages.main_page import MainPage
from ui.pages.settings_page import SettingsPage
from ui.pages.log_panel import LogPanel
from ui.pages.saved_apps_page import SavedAppsPage
from i18n.translations import Translator


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.translator = Translator(config.get('language', 'en'))
        
        self.setWindowTitle(self.translator('app_title'))
        self.setMinimumSize(900, 600)
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        """Initialize UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Navigation bar
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 10, 10, 0)
        
        self.btn_main = QPushButton(self.translator('main_page'))
        self.btn_main.setCheckable(True)
        self.btn_main.clicked.connect(lambda: self.show_page(0))
        
        self.btn_saved = QPushButton(self.translator('saved_apps'))
        self.btn_saved.setCheckable(True)
        self.btn_saved.clicked.connect(lambda: self.show_page(1))
        
        self.btn_log = QPushButton(self.translator('log'))
        self.btn_log.setCheckable(True)
        self.btn_log.clicked.connect(lambda: self.show_page(2))
        
        self.btn_settings = QPushButton(self.translator('settings'))
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(lambda: self.show_page(3))
        
        nav_layout.addWidget(self.btn_main)
        nav_layout.addWidget(self.btn_saved)
        nav_layout.addWidget(self.btn_log)
        nav_layout.addWidget(self.btn_settings)
        nav_layout.addStretch()
        
        main_layout.addLayout(nav_layout)
        
        # Stacked widget for pages
        self.stack = QStackedWidget()
        
        # Create pages
        self.main_page = MainPage(self.config, self.translator, self)
        self.saved_page = SavedAppsPage(self.config, self.translator, self)
        self.log_panel = LogPanel(self.translator)
        self.settings_page = SettingsPage(self.config, self.translator, self)
        
        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.saved_page)
        self.stack.addWidget(self.log_panel)
        self.stack.addWidget(self.settings_page)
        
        main_layout.addWidget(self.stack)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Set default page
        default_page = self.config.get('default_page', 'main')
        page_map = {
            'main': 0,
            'saved': 1,
            'log': 2,
            'settings': 3
        }
        self.show_page(page_map.get(default_page, 0))
    
    def show_page(self, index):
        """Show a specific page"""
        self.stack.setCurrentIndex(index)
        
        # Update button states
        self.btn_main.setChecked(index == 0)
        self.btn_saved.setChecked(index == 1)
        self.btn_log.setChecked(index == 2)
        self.btn_settings.setChecked(index == 3)
    
    def apply_theme(self):
        """Apply theme based on settings"""
        theme = self.config.get('theme', 'system')
        
        if theme == 'dark':
            self.setStyleSheet(self._get_dark_stylesheet())
        elif theme == 'light':
            self.setStyleSheet(self._get_light_stylesheet())
        else:
            # Follow system - detect system theme
            if self._is_system_dark():
                self.setStyleSheet(self._get_dark_stylesheet())
            else:
                self.setStyleSheet(self._get_light_stylesheet())
    
    def _is_system_dark(self):
        """Detect if system is using dark theme"""
        try:
            # Check GTK theme
            import subprocess
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                theme_name = result.stdout.strip().strip("'\"").lower()
                dark_keywords = ['dark', 'black', 'numix', 'arc-dark', 'dracula', 'nordic']
                if any(kw in theme_name for kw in dark_keywords):
                    return True
        except Exception:
            pass
        
        # Fallback: check if dark mode via xdg
        try:
            import subprocess
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and 'dark' in result.stdout.lower():
                return True
        except Exception:
            pass
        
        return False
    
    def _get_dark_stylesheet(self):
        """Get dark theme stylesheet"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #4c4f51;
        }
        QPushButton:checked {
            background-color: #4a86c8;
        }
        QLineEdit, QSpinBox {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 6px;
            border-radius: 4px;
        }
        QComboBox {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 6px;
            border-radius: 4px;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #aaaaaa;
            width: 0;
            height: 0;
        }
        QComboBox QAbstractItemView {
            background-color: #3c3f41;
            color: #ffffff;
            border: 1px solid #555555;
            selection-background-color: #4a86c8;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 10px;
            border: none;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #6a6a6a;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background-color: #2b2b2b;
            height: 10px;
            border: none;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background-color: #555555;
            border-radius: 5px;
            min-width: 30px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #6a6a6a;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        """
    
    def _get_light_stylesheet(self):
        """Get light theme stylesheet"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
            color: #333333;
        }
        QWidget {
            background-color: #f5f5f5;
            color: #333333;
        }
        QPushButton {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #e8e8e8;
        }
        QPushButton:checked {
            background-color: #4a86c8;
            color: #ffffff;
        }
        QLineEdit, QSpinBox {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 6px;
            border-radius: 4px;
        }
        QComboBox {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            padding: 6px;
            border-radius: 4px;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #666666;
            width: 0;
            height: 0;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
            selection-background-color: #4a86c8;
            selection-color: #ffffff;
        }
        QGroupBox {
            border: 1px solid #cccccc;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #cccccc;
        }
        QScrollBar:vertical {
            background-color: #f5f5f5;
            width: 10px;
            border: none;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background-color: #cccccc;
            border-radius: 5px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #aaaaaa;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background-color: #f5f5f5;
            height: 10px;
            border: none;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background-color: #cccccc;
            border-radius: 5px;
            min-width: 30px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #aaaaaa;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
        """
    
    def refresh_ui(self):
        """Refresh UI after settings change"""
        self.translator.set_language(self.config.get('language', 'en'))
        self.setWindowTitle(self.translator('app_title'))
        
        # Update navigation buttons
        self.btn_main.setText(self.translator('main_page'))
        self.btn_saved.setText(self.translator('saved_apps'))
        self.btn_log.setText(self.translator('log'))
        self.btn_settings.setText(self.translator('settings'))
        
        # Refresh pages
        self.main_page.refresh()
        self.saved_page.refresh()
        self.log_panel.refresh()
        self.settings_page.refresh()
        
        # Apply theme
        self.apply_theme()
    
    def log_message(self, message, level='info'):
        """Log a message"""
        self.log_panel.log(message, level)
    
    def show_log(self):
        """Show log page"""
        self.show_page(2)
