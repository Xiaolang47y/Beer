# -*- coding: utf-8 -*-
"""Background task for extracting an icon from a Windows executable."""

from PyQt6.QtCore import QThread, pyqtSignal


class IconExtractTask(QThread):
    """Run :meth:`IconExtractor.extract_icon` without blocking the GUI."""

    extracted = pyqtSignal(str, str)  # icon_path, error

    def __init__(self, extractor, exe_path, parent=None):
        super().__init__(parent)
        self.extractor = extractor
        self.exe_path = exe_path

    def run(self):
        try:
            icon_path, error = self.extractor.extract_icon(self.exe_path)
        except Exception as exc:  # pragma: no cover - defensive
            icon_path, error = '', str(exc)
        self.extracted.emit(icon_path or '', error or '')
