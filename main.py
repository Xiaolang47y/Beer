#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beer - Be Emulator morE Ruined
A GUI for running Windows programs through Proton without Steam.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from core.config_manager import ConfigManager
from core.app_icon import get_app_icon
from core.version import APP_NAME, APP_VERSION


def main():
    # Enable high DPI scaling
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(get_app_icon())

    # Initialize config manager
    config = ConfigManager()

    # Create and show main window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
