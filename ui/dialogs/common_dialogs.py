# -*- coding: utf-8 -*-
"""Small reusable dialogs for the saved applications page."""

import os

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QLabel,
    QLineEdit, QVBoxLayout,
)

from ui.pages.app_helpers import enable_ime
from ui.widgets import BeerComboBox


class SimpleInputDialog(QDialog):
    """A minimal dialog with a title and a single text input."""

    def __init__(self, title='', default_text='', translator=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        self.translator = translator

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.input_field = QLineEdit(default_text)
        self.input_field.selectAll()
        enable_ime(self.input_field)
        layout.addWidget(self.input_field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        if translator is not None:
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
                translator('ok')
            )
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
                translator('cancel')
            )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.input_field.text()


class RuntimeSelectDialog(QDialog):
    """Choose a Proton/Wine runtime, optionally browsing for a custom path."""

    BROWSE_DATA = '__browse__'

    def __init__(self, current_path, runtimes, translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self._browse_path = ''
        self.setWindowTitle(translator('select_runtime'))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.combo = BeerComboBox()
        for runtime in runtimes or []:
            label = '{} · {} ({})'.format(
                runtime.get('name', runtime.get('path', '')),
                runtime.get('version_str', ''),
                translator('runtime_type_' + runtime.get('type', 'proton')),
            )
            self.combo.addItem(label, runtime.get('path', ''))
        self.combo.addItem(translator('browse') + '…', self.BROWSE_DATA)

        if current_path:
            index = self.combo.findData(current_path)
            if index >= 0:
                self.combo.setCurrentIndex(index)
            else:
                self.combo.insertItem(
                    0, os.path.basename(current_path) or current_path, current_path
                )
                self.combo.setCurrentIndex(0)

        layout.addWidget(self.combo)

        hint = QLabel(translator('runtime_custom_hint'))
        hint.setWordWrap(True)
        hint.setStyleSheet('color: gray; font-size: 10px;')
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            translator('ok')
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            translator('cancel')
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if self.combo.currentData() == self.BROWSE_DATA:
            directory = QFileDialog.getExistingDirectory(
                self, self.translator('select_runtime')
            )
            if directory:
                self._browse_path = directory
                self.accept()
            return
        self.accept()

    def get_runtime_path(self):
        if self.combo.currentData() == self.BROWSE_DATA:
            return self._browse_path
        return self.combo.currentData()
