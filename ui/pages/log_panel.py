# -*- coding: utf-8 -*-
"""
Log page for Beer
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor


class LogPanel(QWidget):
    """Log page widget"""
    
    def __init__(self, translator):
        super().__init__()
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
        
        # Clear button
        self.btn_clear = QPushButton(self.translator('clear_log'))
        self.btn_clear.clicked.connect(self.clear_log)
        header_layout.addWidget(self.btn_clear)
        
        # Save button
        self.btn_save = QPushButton(self.translator('save_log'))
        self.btn_save.clicked.connect(self.save_log)
        header_layout.addWidget(self.btn_save)
        
        layout.addLayout(header_layout)
        
        # Log text area (fills the page)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
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
        """Log a message with level"""
        colors = {
            'info': '#ffffff',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'proton': '#56b6c2'
        }

        color = colors.get(level, '#ffffff')

        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}"

        self.log_text.append(f'<span style="color: {color};">{formatted_msg}</span>')

        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
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
        self.btn_clear.setText(self.translator('clear_log'))
        self.btn_save.setText(self.translator('save_log'))
