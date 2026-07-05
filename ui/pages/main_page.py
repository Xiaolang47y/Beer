# -*- coding: utf-8 -*-
"""
Main page for Beer
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFileDialog, QGroupBox, QCheckBox,
    QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from core.proton_manager import ProtonManager
from core.icon_extractor import IconExtractor
from core.desktop_generator import DesktopGenerator
from ui.dialogs.more_options_dialog import MoreOptionsDialog


def _popup_background_color(combo):
    """Return the background colour the popup container should use.

    Qt stylesheets do not reliably update QWidget.palette(), so we inspect the
    stylesheet that is actually applied to the combo or its ancestors.
    """
    widget = combo
    while widget is not None:
        ss = widget.styleSheet()
        if ss:
            # Dark theme stylesheet sets the main window to #2b2b2b and the
            # combo view to #3c3f41.
            if '#2b2b2b' in ss or '#3c3f41' in ss:
                return '#3c3f41'
            # Light theme stylesheet sets the main window to #f5f5f5 and the
            # combo view to #ffffff.
            if '#f5f5f5' in ss or '#ffffff' in ss:
                return '#ffffff'
        widget = widget.parent()
    return '#ffffff'


def fix_combobox_frame(combo):
    """Remove the white/black bars around a combo box dropdown popup.

    The popup container is painted with the theme's combo-view background colour
    so any exposed edges blend in.  Frame and layout margins are also removed.
    """
    view = combo.view()
    if view is None:
        return
    view.setFrameShape(QFrame.Shape.NoFrame)

    container = view.parentWidget()
    if container is not None and isinstance(container, QFrame):
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setFrameShadow(QFrame.Shadow.Plain)
        container.setLineWidth(0)
        container.setMidLineWidth(0)
        container.setContentsMargins(0, 0, 0, 0)

        layout = container.layout()
        if layout is not None:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        bg = _popup_background_color(combo)
        container.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: none; }}"
        )


class FramelessComboBox(QComboBox):
    """ComboBox with no dropdown white frame and no scroll-wheel change"""
    def __init__(self, parent=None):
        super().__init__(parent)

    def _fix_popup_frame(self):
        fix_combobox_frame(self)

    def showPopup(self):
        super().showPopup()
        self._fix_popup_frame()

    def wheelEvent(self, event):
        event.ignore()


class MainPage(QWidget):
    """Main page widget"""
    
    def __init__(self, config, translator, main_window):
        super().__init__()
        self.config = config
        self.translator = translator
        self.main_window = main_window
        
        self.proton_manager = None
        self.icon_extractor = None
        self.desktop_generator = DesktopGenerator()
        
        self.more_options = {}
        
        self.init_ui()
        self.load_proton_versions()
    
    def init_ui(self):
        """Initialize UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Main widget
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Proton version selection
        self.proton_group = QGroupBox(self.translator('proton_version'))
        proton_layout = QVBoxLayout(self.proton_group)
        
        self.proton_desc = QLabel(self.translator('proton_desc'))
        self.proton_desc.setWordWrap(True)
        self.proton_desc.setStyleSheet("color: gray; font-size: 11px;")
        proton_layout.addWidget(self.proton_desc)
        
        proton_row = QHBoxLayout()
        self.proton_combo = FramelessComboBox()
        self.proton_combo.setMinimumWidth(200)
        proton_row.addWidget(self.proton_combo)
        proton_row.addStretch()
        
        proton_layout.addLayout(proton_row)
        
        self.proton_warning = QLabel(self.translator('custom_proton_enabled'))
        self.proton_warning.setStyleSheet("color: orange; font-size: 11px;")
        self.proton_warning.hide()
        proton_layout.addWidget(self.proton_warning)
        
        layout.addWidget(self.proton_group)
        
        # Program path
        self.program_group = QGroupBox(self.translator('program_path'))
        program_layout = QVBoxLayout(self.program_group)
        
        self.program_desc = QLabel(self.translator('program_desc'))
        self.program_desc.setWordWrap(True)
        self.program_desc.setStyleSheet("color: gray; font-size: 11px;")
        program_layout.addWidget(self.program_desc)
        
        program_row = QHBoxLayout()
        self.program_path = QLineEdit()
        self.program_path.setPlaceholderText("/path/to/program.exe")
        program_row.addWidget(self.program_path)
        
        self.btn_browse_program = QPushButton(self.translator('browse'))
        self.btn_browse_program.clicked.connect(self.browse_program)
        program_row.addWidget(self.btn_browse_program)
        
        program_layout.addLayout(program_row)
        layout.addWidget(self.program_group)
        
        # Run directory
        self.run_dir_group = QGroupBox(self.translator('run_directory'))
        run_dir_layout = QVBoxLayout(self.run_dir_group)
        
        self.run_dir_desc = QLabel(self.translator('run_dir_desc'))
        self.run_dir_desc.setWordWrap(True)
        self.run_dir_desc.setStyleSheet("color: gray; font-size: 11px;")
        run_dir_layout.addWidget(self.run_dir_desc)
        
        run_dir_row = QHBoxLayout()
        self.run_directory = QLineEdit()
        self.run_directory.setPlaceholderText("/path/to/working/directory")
        run_dir_row.addWidget(self.run_directory)
        
        self.btn_browse_run_dir = QPushButton(self.translator('browse'))
        self.btn_browse_run_dir.clicked.connect(self.browse_run_directory)
        run_dir_row.addWidget(self.btn_browse_run_dir)
        
        run_dir_layout.addLayout(run_dir_row)
        layout.addWidget(self.run_dir_group)
        
        # Program name
        self.name_group = QGroupBox(self.translator('program_name'))
        name_layout = QVBoxLayout(self.name_group)
        
        self.name_desc = QLabel(self.translator('program_name_desc'))
        self.name_desc.setWordWrap(True)
        self.name_desc.setStyleSheet("color: gray; font-size: 11px;")
        name_layout.addWidget(self.name_desc)
        
        self.program_name = QLineEdit()
        self.program_name.setPlaceholderText("My Program")
        name_layout.addWidget(self.program_name)
        
        layout.addWidget(self.name_group)
        
        # Architecture selection
        self.arch_group = QGroupBox(self.translator('architecture'))
        arch_layout = QVBoxLayout(self.arch_group)
        
        self.arch_desc = QLabel(self.translator('arch_desc'))
        self.arch_desc.setWordWrap(True)
        self.arch_desc.setStyleSheet("color: gray; font-size: 11px;")
        arch_layout.addWidget(self.arch_desc)
        
        arch_row = QHBoxLayout()
        self.arch_combo = FramelessComboBox()
        self.arch_combo.addItem(self.translator('arch_auto'), 'auto')
        self.arch_combo.addItem(self.translator('arch_32'), '32')
        self.arch_combo.addItem(self.translator('arch_64'), '64')
        self.arch_combo.setMinimumWidth(150)
        arch_row.addWidget(self.arch_combo)
        
        self.arch_info = QLabel()
        self.arch_info.setStyleSheet("color: gray; font-size: 11px;")
        arch_row.addWidget(self.arch_info)
        arch_row.addStretch()
        
        arch_layout.addLayout(arch_row)
        
        # Architecture descriptions
        arch_info_layout = QVBoxLayout()
        arch_info_layout.setContentsMargins(10, 5, 0, 0)
        
        self.info_32 = QLabel(f"• {self.translator('arch_32')}: {self.translator('arch_32_desc')}")
        self.info_32.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_32)
        
        self.info_64 = QLabel(f"• {self.translator('arch_64')}: {self.translator('arch_64_desc')}")
        self.info_64.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_64)
        
        self.info_auto = QLabel(f"• {self.translator('arch_auto')}: {self.translator('arch_auto_desc')}")
        self.info_auto.setStyleSheet("color: gray; font-size: 10px;")
        arch_info_layout.addWidget(self.info_auto)
        
        arch_layout.addLayout(arch_info_layout)
        
        layout.addWidget(self.arch_group)
        layout.addStretch()
        
        scroll.setWidget(main_widget)
        main_layout.addWidget(scroll)
        
        # Buttons (fixed at bottom, not scrolling)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(20, 10, 20, 20)
        
        self.btn_more_options = QPushButton(self.translator('more_options'))
        self.btn_more_options.clicked.connect(self.show_more_options)
        button_layout.addWidget(self.btn_more_options)
        
        self.btn_save_config = QPushButton(self.translator('save_config'))
        self.btn_save_config.clicked.connect(self.save_config)
        button_layout.addWidget(self.btn_save_config)
        
        self.btn_run = QPushButton(self.translator('run'))
        self.btn_run.setStyleSheet("background-color: #4a86c8; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self.run_program)
        button_layout.addWidget(self.btn_run)
        
        self.btn_generate_desktop = QPushButton(self.translator('generate_desktop'))
        self.btn_generate_desktop.clicked.connect(self.generate_desktop_file)
        button_layout.addWidget(self.btn_generate_desktop)
        
        main_layout.addLayout(button_layout)
    
    def load_proton_versions(self):
        """Load available Proton versions"""
        # Always initialize proton_manager for launching
        search_paths = self.config.get('proton_search_paths', [])
        self.proton_manager = ProtonManager(search_paths)
        
        if self.config.get('custom_proton_enabled'):
            self.proton_combo.setEnabled(False)
            self.proton_warning.show()
            return
        
        self.proton_combo.setEnabled(True)
        self.proton_warning.hide()
        
        self.proton_combo.clear()
        for proton in self.proton_manager.get_proton_versions():
            self.proton_combo.addItem(proton['name'], proton['path'])
        
        if self.proton_combo.count() == 0:
            self.proton_combo.addItem("No Proton found", "")
    
    def browse_program(self):
        """Browse for executable file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('select_exe'),
            "",
            f"{self.translator('exe_files')} (*.exe);;{self.translator('all_files')} (*)"
        )
        
        if file_path:
            self.program_path.setText(file_path)
            
            # Auto-fill program name
            if not self.program_name.text():
                import os
                name = os.path.splitext(os.path.basename(file_path))[0]
                self.program_name.setText(name)
            
            # Auto-fill run directory
            if not self.run_directory.text():
                import os
                self.run_directory.setText(os.path.dirname(file_path))
    
    def browse_run_directory(self):
        """Browse for run directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('select_directory')
        )
        
        if directory:
            self.run_directory.setText(directory)
    
    def show_more_options(self):
        """Show more options dialog"""
        dialog = MoreOptionsDialog(self.more_options, self.translator, self)
        if dialog.exec():
            self.more_options = dialog.get_options()
    
    def save_config(self):
        """Save current configuration"""
        app_config = self._get_app_config()
        name = app_config.get('name', '')
        
        if not name:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                "Please enter a program name"
            )
            return
        
        # Check for duplicate name
        existing_apps = self.config.get_apps()
        for app in existing_apps:
            if app.get('name') == name:
                reply = QMessageBox.question(
                    self,
                    self.translator('warning'),
                    self.translator('duplicate_name'),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                break
        
        if self.config.save_app(app_config):
            self.main_window.log_message(self.translator('config_saved'), 'success')
            QMessageBox.information(
                self,
                self.translator('success'),
                self.translator('config_saved')
            )
            # Refresh saved apps page immediately
            self.main_window.saved_page.refresh()
    
    def _get_app_config(self):
        """Get current configuration as dict"""
        # Extract and persist icon for this app
        icon_path = ''
        exe_path = self.program_path.text()
        if exe_path and os.path.exists(exe_path):
            if self.icon_extractor is None:
                self.icon_extractor = IconExtractor(
                    icons_dir=self.config.get_icons_dir()
                )
            if self.icon_extractor.is_tool_available():
                extracted, error = self.icon_extractor.extract_icon(exe_path)
                if extracted:
                    icon_path = extracted

        return {
            'name': self.program_name.text(),
            'proton_path': self.proton_combo.currentData(),
            'exe_path': exe_path,
            'run_directory': self.run_directory.text(),
            'architecture': self.arch_combo.currentData(),
            'more_options': self.more_options,
            'icon_path': icon_path
        }
    
    def run_program(self):
        """Run the program with Proton"""
        # Validate inputs
        exe_path = self.program_path.text()
        if not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                self.translator('exe_not_found')
            )
            return
        
        import os
        if not os.path.exists(exe_path):
            QMessageBox.warning(
                self,
                self.translator('error'),
                self.translator('exe_not_found')
            )
            return
        
        # Get Proton path - always use custom path if enabled
        if self.config.get('custom_proton_enabled'):
            proton_path = self.config.get('custom_proton_path')
            if not proton_path:
                QMessageBox.warning(
                    self,
                    self.translator('error'),
                    self.translator('proton_not_found')
                )
                return
        else:
            proton_path = self.proton_combo.currentData()
            if not proton_path:
                QMessageBox.warning(
                    self,
                    self.translator('error'),
                    self.translator('proton_not_found')
                )
                return
        
        # Run pre-launch script if configured
        pre_launch_script = self.more_options.get('pre_launch_script')
        if pre_launch_script:
            self._run_script(pre_launch_script)
        
        # Launch program
        self.main_window.log_message(f"Launching: {exe_path}", 'info')
        if self.config.get('show_log_on_start', False):
            self.main_window.show_log()
        
        env_vars = self.config.get('environment_variables', {})
        args = self.more_options.get('startup_args', '').split() if self.more_options.get('startup_args') else None
        working_dir = self.run_directory.text() or os.path.dirname(exe_path)

        success, result = self.proton_manager.launch_program(
            proton_path, exe_path, working_dir, env_vars, args,
            output_callback=self.main_window.log_message
        )
        
        if success:
            self.main_window.log_message(self.translator('launch_success'), 'success')
            
            # Handle batch launch
            batch_apps = self.more_options.get('batch_apps', [])
            if batch_apps:
                self._batch_launch(batch_apps)
        else:
            self.main_window.log_message(f"{self.translator('launch_failed')}: {result}", 'error')
    
    def _run_script(self, script_path):
        """Run a shell script"""
        import subprocess
        try:
            subprocess.run(['bash', script_path], check=True)
            self.main_window.log_message(f"Script executed: {script_path}", 'info')
        except Exception as e:
            self.main_window.log_message(f"Script failed: {e}", 'error')
    
    def _batch_launch(self, batch_apps):
        """Launch multiple applications in sequence"""
        import time
        interval = self.more_options.get('launch_interval', 0)
        
        for app in batch_apps:
            if interval > 0:
                time.sleep(interval)
            
            self.main_window.log_message(f"Batch launching: {app.get('name')}", 'info')
            # Launch each app...
    
    def generate_desktop_file(self):
        """Generate desktop file"""
        # Initialize icon extractor with persistent icons dir
        self.icon_extractor = IconExtractor(
            icons_dir=self.config.get_icons_dir()
        )

        # Get configuration
        name = self.program_name.text()
        exe_path = self.program_path.text()

        if not name or not exe_path:
            QMessageBox.warning(
                self,
                self.translator('warning'),
                "Please fill in program name and path"
            )
            return

        # Extract icon (saved to persistent location)
        icon_path = None
        if self.icon_extractor.is_tool_available():
            icon_path, error = self.icon_extractor.extract_icon(exe_path)
            if error:
                self.main_window.log_message(f"Icon extraction failed: {error}", 'warning')
        
        # Get Proton path
        if self.config.get('custom_proton_enabled'):
            proton_path = self.config.get('custom_proton_path')
        else:
            proton_path = self.proton_combo.currentData()
        
        # Generate desktop file
        env_vars = self.config.get('environment_variables', {})
        args = self.more_options.get('startup_args', '').split() if self.more_options.get('startup_args') else None
        working_dir = self.run_directory.text()
        
        success, result = self.desktop_generator.generate_desktop_file(
            name=name,
            exe_path=exe_path,
            icon_path=icon_path,
            working_dir=working_dir,
            proton_path=proton_path,
            env_vars=env_vars,
            args=args
        )
        
        if success:
            self.main_window.log_message(self.translator('desktop_file_generated'), 'success')
            QMessageBox.information(
                self,
                self.translator('success'),
                f"{self.translator('desktop_file_generated')}\n{result}"
            )
        else:
            self.main_window.log_message(f"Desktop file generation failed: {result}", 'error')
    
    def refresh(self):
        """Refresh the page"""
        self.load_proton_versions()

        # Update group box titles
        self.proton_group.setTitle(self.translator('proton_version'))
        self.program_group.setTitle(self.translator('program_path'))
        self.run_dir_group.setTitle(self.translator('run_directory'))
        self.name_group.setTitle(self.translator('program_name'))
        self.arch_group.setTitle(self.translator('architecture'))

        # Update description labels
        self.proton_desc.setText(self.translator('proton_desc'))
        self.program_desc.setText(self.translator('program_desc'))
        self.run_dir_desc.setText(self.translator('run_dir_desc'))
        self.name_desc.setText(self.translator('program_name_desc'))
        self.arch_desc.setText(self.translator('arch_desc'))

        # Update architecture info labels
        self.info_32.setText(f"• {self.translator('arch_32')}: {self.translator('arch_32_desc')}")
        self.info_64.setText(f"• {self.translator('arch_64')}: {self.translator('arch_64_desc')}")
        self.info_auto.setText(f"• {self.translator('arch_auto')}: {self.translator('arch_auto_desc')}")

        # Update buttons
        self.btn_browse_program.setText(self.translator('browse'))
        self.btn_browse_run_dir.setText(self.translator('browse'))
        self.btn_more_options.setText(self.translator('more_options'))
        self.btn_save_config.setText(self.translator('save_config'))
        self.btn_run.setText(self.translator('run'))
        self.btn_generate_desktop.setText(self.translator('generate_desktop'))

        # Update warning / placeholders
        self.proton_warning.setText(self.translator('custom_proton_enabled'))
        self.program_name.setPlaceholderText(self.translator('program_name'))

        # Update combo box item texts (keep user data)
        self._update_combo_item_text(self.arch_combo, {
            'auto': self.translator('arch_auto'),
            '32': self.translator('arch_32'),
            '64': self.translator('arch_64'),
        })

    def _update_combo_item_text(self, combo, data_to_text):
        """Update display text for combo box items while preserving user data"""
        current_data = combo.currentData()
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data in data_to_text:
                combo.setItemText(i, data_to_text[data])
        if current_data is not None:
            index = combo.findData(current_data)
            if index >= 0:
                combo.setCurrentIndex(index)
