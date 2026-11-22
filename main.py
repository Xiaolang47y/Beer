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


def _extend_qt_plugin_paths():
    """Let source runs find the system input method plugins (fcitx/ibus).

    PyQt6 restricts Qt's plugin search path to its own directory, which does
    not contain the distribution's fcitx plugin.  The packaged build bundles
    those plugins already, so this only applies when running from source.
    """
    if getattr(sys, 'frozen', False):
        return
    import glob

    roots = [
        '/usr/lib/x86_64-linux-gnu/qt6/plugins',
        '/usr/lib64/qt6/plugins',
        '/usr/lib/qt6/plugins',
    ]
    roots.extend(glob.glob('/usr/lib/*/qt6/plugins'))
    existing = os.environ.get('QT_PLUGIN_PATH', '')
    paths = [
        root for root in roots
        if os.path.isdir(os.path.join(root, 'platforminputcontexts'))
    ]
    if existing:
        paths.append(existing)
    if paths:
        os.environ['QT_PLUGIN_PATH'] = os.pathsep.join(paths)


def _run_headless(argv):
    """Handle ``--run-app`` / ``--record-app`` without starting the GUI."""
    from core.app_runner import cli_main
    return cli_main(argv)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('--run-app', '--record-app'):
        sys.exit(_run_headless(sys.argv[1:]))

    # Enable high DPI scaling
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    _extend_qt_plugin_paths()

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
