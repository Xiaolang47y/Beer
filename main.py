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
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from core.config_manager import ConfigManager


def main():
    # Enable high DPI scaling
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    app = QApplication(sys.argv)
    app.setApplicationName('Beer')
    app.setApplicationDisplayName('Beer')

    # Initialize config manager
    config = ConfigManager()

    # Create and show main window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
