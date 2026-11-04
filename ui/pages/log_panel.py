# -*- coding: utf-8 -*-
"""
Log page for Beer
"""

import datetime
import html

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QCheckBox
)


class LogPanel(QWidget):
    """Log page widget"""

    LEVEL_COLORS = {
        'info': '#ffffff',
        'success': '#4caf50',
        'warning': '#ff9800',
        'error': '#f44336',
        'proton': '#56b6c2',
    }

    def __init__(self, config, translator):
        super().__init__()
        self.config = config
        self.translator = translator

        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        self.title = QLabel(self.translator('log'))
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.title)

        header_layout.addStretch()

        self.chk_auto_scroll = QCheckBox(self.translator('log_auto_scroll'))
        self.chk_auto_scroll.setToolTip(self.translator('log_auto_scroll_desc'))
        auto_scroll = True
        if self.config is not None:
            auto_scroll = bool(self.config.get('log_auto_scroll', True))
        self.chk_auto_scroll.setChecked(auto_scroll)
        self.chk_auto_scroll.toggled.connect(self.on_auto_scroll_changed)
        header_layout.addWidget(self.chk_auto_scroll)

        # Clear button
        self.btn_clear = QPushButton(self.translator('clear_log'))
        self.btn_clear.clicked.connect(self.clear_log)
        header_layout.addWidget(self.btn_clear)

        # Save button
        self.btn_save = QPushButton(self.translator('save_log'))
        self.btn_save.clicked.connect(self.save_log)
        header_layout.addWidget(self.btn_save)

        layout.addLayout(header_layout)

        # Log text area (fills the page).  Terminal output is kept verbatim,
        # so line wrapping is disabled and a horizontal scrollbar is available.
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)

    def log(self, message, level='info'):
        """Log a message with level (HTML is escaped, full output is kept)."""
        color = self.LEVEL_COLORS.get(level, '#ffffff')
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')

        message = '' if message is None else str(message)
        # Keep the complete terminal output, including multi-line chunks.
        lines = message.split('\n')
        if lines and lines[-1] == '':
            lines = lines[:-1]

        blocks = []
        for index, line in enumerate(lines):
            escaped = html.escape(line)
            # Preserve indentation and terminal-style spacing.
            escaped = escaped.replace(' ', '&nbsp;').replace('\t', '&nbsp;' * 4)
            if index == 0:
                escaped = f"[{timestamp}] {escaped}"
            blocks.append(f'<span style="color: {color};">{escaped}</span>')

        if not blocks:
            blocks.append(
                f'<span style="color: {color};">[{timestamp}] </span>'
            )

        scrollbar = self.log_text.verticalScrollBar()
        old_value = scrollbar.value()

        for block in blocks:
            self.log_text.append(block)

        if self.chk_auto_scroll.isChecked():
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(old_value)

    def on_auto_scroll_changed(self, checked):
        """Persist the auto-scroll preference."""
        if self.config is not None:
            self.config.set('log_auto_scroll', bool(checked))
        if checked:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """Clear log"""
        self.log_text.clear()

    def save_log(self):
        """Save log to file"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translator('save_log'),
            "",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log(f"Log saved to {file_path}", 'success')
            except Exception as e:
                self.log(f"Failed to save log: {e}", 'error')

    def refresh(self):
        """Refresh texts"""
        self.title.setText(self.translator('log'))
        self.chk_auto_scroll.setText(self.translator('log_auto_scroll'))
        self.chk_auto_scroll.setToolTip(self.translator('log_auto_scroll_desc'))
        self.btn_clear.setText(self.translator('clear_log'))
        self.btn_save.setText(self.translator('save_log'))
