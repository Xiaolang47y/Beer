# -*- coding: utf-8 -*-
"""Save-application dialog shown when saving a configuration from the main page."""

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout,
)

from ui.pages.app_helpers import enable_ime


class SaveAppDialog(QDialog):
    """Collect the name, description and categories before saving an app."""

    def __init__(self, translator, name='', description='', tags=None,
                 runtime_label='', exe_path='', parent=None):
        super().__init__(parent)
        self.translator = translator
        self.setWindowTitle(translator('save_app_title'))
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        intro = QLabel(translator('save_app_desc'))
        intro.setWordWrap(True)
        intro.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(intro)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.txt_name = QLineEdit(name)
        enable_ime(self.txt_name)
        form.addRow(translator('desktop_name'), self.txt_name)

        self.txt_description = QLineEdit(description)
        enable_ime(self.txt_description)
        self.txt_description.setPlaceholderText(translator('save_app_desc_placeholder'))
        form.addRow(translator('edit_desc'), self.txt_description)

        self.txt_tags = QLineEdit(', '.join(tags or []))
        enable_ime(self.txt_tags)
        self.txt_tags.setPlaceholderText(translator('tags_placeholder'))
        form.addRow(translator('categories'), self.txt_tags)

        runtime_value = QLabel(runtime_label or '-')
        form.addRow(translator('runtime_short'), runtime_value)

        exe_value = QLabel(exe_path or '-')
        exe_value.setWordWrap(True)
        exe_value.setStyleSheet('color: gray; font-size: 10px;')
        form.addRow(translator('program_path'), exe_value)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            translator('save')
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            translator('cancel')
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        raw = self.txt_tags.text().replace('，', ',')
        tags = []
        for part in raw.replace(';', ',').split(','):
            tag = part.strip()
            if tag and tag not in tags:
                tags.append(tag)
        return {
            'name': self.txt_name.text().strip(),
            'description': self.txt_description.text().strip(),
            'tags': tags,
        }
