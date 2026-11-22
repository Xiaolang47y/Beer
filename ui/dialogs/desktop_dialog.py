# -*- coding: utf-8 -*-
"""
Desktop entry options dialog for Beer.
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QCheckBox, QPushButton, QVBoxLayout,
    QPlainTextEdit, QWidget, QMessageBox, QScrollArea, QProgressDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.desktop_generator import (
    DesktopGenerator,
    sanitize_filename,
)
from ui.icon_extract_task import IconExtractTask
from ui.pages.app_helpers import enable_ime
from ui.widgets import BeerComboBox


class DesktopEntryDialog(QDialog):
    """Dialog used to review and adjust the generated .desktop file."""

    def __init__(self, options, translator, runtimes=None,
                 icon_extractor=None, parent=None):
        super().__init__(parent)
        options = dict(options or {})
        self.translator = translator
        self.runtimes = runtimes or []
        self.icon_extractor = icon_extractor
        self.generator = DesktopGenerator()
        # The filename follows the application name until the user edits it.
        self._filename_edited = False
        self._updating = False
        self._icon_tasks = []
        self._app_id = options.get('app_id', '')
        self._compat_data_path = options.get('compat_data_path', '')

        self.setWindowTitle(self.translator('desktop_settings'))
        self.resize(880, 720)
        self.setMinimumSize(760, 540)

        self.init_ui()
        self.load_options(options)
        self.update_preview()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def init_ui(self):
        outer_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

        intro = QLabel(self.translator('desktop_settings_desc'))
        intro.setWordWrap(True)
        intro.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(intro)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        self.txt_name = QLineEdit()
        self.txt_name.textChanged.connect(self.on_name_changed)
        enable_ime(self.txt_name)
        form.addRow(self.translator('desktop_name'), self.txt_name)

        self.txt_comment = QLineEdit()
        enable_ime(self.txt_comment)
        form.addRow(self.translator('desktop_comment'), self.txt_comment)

        exe_row = QWidget()
        exe_layout = QHBoxLayout(exe_row)
        exe_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_exe = QLineEdit()
        self.txt_exe.textChanged.connect(self.update_preview)
        exe_layout.addWidget(self.txt_exe)
        self.btn_browse_exe = QPushButton(self.translator('browse'))
        self.btn_browse_exe.clicked.connect(self.browse_exe)
        exe_layout.addWidget(self.btn_browse_exe)
        form.addRow(self.translator('desktop_exe'), exe_row)

        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_working_dir = QLineEdit()
        self.txt_working_dir.textChanged.connect(self.update_preview)
        dir_layout.addWidget(self.txt_working_dir)
        self.btn_browse_dir = QPushButton(self.translator('browse'))
        self.btn_browse_dir.clicked.connect(self.browse_working_dir)
        dir_layout.addWidget(self.btn_browse_dir)
        form.addRow(self.translator('desktop_working_dir'), dir_row)

        self.combo_runtime = BeerComboBox()
        self.combo_runtime.addItem(self.translator('desktop_no_runtime'), '')
        for runtime in self.runtimes:
            label = '{} · {} ({})'.format(
                runtime.get('name', ''),
                runtime.get('version_str', ''),
                self.translator('runtime_type_' + runtime.get('type', 'proton'))
            )
            self.combo_runtime.addItem(label, runtime.get('path', ''))
        self.combo_runtime.currentIndexChanged.connect(self.update_preview)
        form.addRow(self.translator('desktop_runtime'), self.combo_runtime)

        icon_row = QWidget()
        icon_layout = QHBoxLayout(icon_row)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        self.txt_icon = QLineEdit()
        self.txt_icon.textChanged.connect(self.update_preview)
        icon_layout.addWidget(self.txt_icon)
        self.btn_browse_icon = QPushButton(self.translator('browse'))
        self.btn_browse_icon.clicked.connect(self.browse_icon)
        icon_layout.addWidget(self.btn_browse_icon)
        self.btn_emoji_icon = QPushButton('🍺')
        self.btn_emoji_icon.setToolTip(self.translator('desktop_use_emoji_icon'))
        self.btn_emoji_icon.setFixedWidth(42)
        self.btn_emoji_icon.clicked.connect(self.use_emoji_icon)
        icon_layout.addWidget(self.btn_emoji_icon)
        self.btn_extract_icon = QPushButton(self.translator('desktop_extract_icon'))
        self.btn_extract_icon.clicked.connect(self.extract_icon)
        icon_layout.addWidget(self.btn_extract_icon)
        form.addRow(self.translator('desktop_icon'), icon_row)

        self.txt_args = QLineEdit()
        self.txt_args.textChanged.connect(self.update_preview)
        form.addRow(self.translator('desktop_args'), self.txt_args)

        self.txt_categories = QLineEdit()
        self.txt_categories.textChanged.connect(self.update_preview)
        form.addRow(self.translator('desktop_categories'), self.txt_categories)

        self.chk_terminal = QCheckBox(self.translator('desktop_terminal'))
        self.chk_terminal.toggled.connect(self.update_preview)
        form.addRow('', self.chk_terminal)

        location_row = QWidget()
        location_layout = QHBoxLayout(location_row)
        location_layout.setContentsMargins(0, 0, 0, 0)
        self.combo_target = BeerComboBox()
        self.combo_target.addItem(self.translator('desktop_target_desktop'), 'desktop')
        self.combo_target.addItem(self.translator('desktop_target_applications'), 'applications')
        self.combo_target.addItem(self.translator('desktop_target_custom'), 'custom')
        self.combo_target.currentIndexChanged.connect(self.on_target_changed)
        location_layout.addWidget(self.combo_target)
        self.txt_custom_dir = QLineEdit()
        self.txt_custom_dir.setPlaceholderText(self.translator('desktop_custom_dir'))
        self.txt_custom_dir.textChanged.connect(self.update_preview)
        location_layout.addWidget(self.txt_custom_dir)
        self.btn_browse_target = QPushButton(self.translator('browse'))
        self.btn_browse_target.clicked.connect(self.browse_target_dir)
        location_layout.addWidget(self.btn_browse_target)
        form.addRow(self.translator('desktop_location'), location_row)

        self.txt_filename = QLineEdit()
        self.txt_filename.setPlaceholderText('my-program.desktop')
        self.txt_filename.textEdited.connect(self.on_filename_edited)
        self.txt_filename.textChanged.connect(self.update_preview)
        form.addRow(self.translator('desktop_filename'), self.txt_filename)

        layout.addLayout(form)

        self.lbl_env = QLabel('')
        self.lbl_env.setWordWrap(True)
        self.lbl_env.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.lbl_env)

        preview_label = QLabel(self.translator('desktop_preview'))
        preview_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(preview_label)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(200)
        font = QFont('Monospace')
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        self.preview.setFont(font)
        layout.addWidget(self.preview)

        self.lbl_status = QLabel('')
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            self.translator('desktop_generate')
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            self.translator('cancel')
        )
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        outer_layout.addWidget(self.buttons)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def load_options(self, options):
        self._updating = True
        self.txt_name.setText(options.get('name', ''))
        self.txt_comment.setText(options.get('comment', '') or options.get('name', ''))
        self.txt_exe.setText(options.get('exe_path', ''))
        self.txt_working_dir.setText(options.get('working_dir', ''))
        self.txt_args.setText(options.get('args', ''))
        self.txt_categories.setText(options.get('categories', 'Game;'))
        self.chk_terminal.setChecked(bool(options.get('terminal', False)))
        self.txt_icon.setText(
            options.get('icon_path', '') or self.generator.default_icon_path
        )

        runtime_path = options.get('runtime_path', '')
        index = self.combo_runtime.findData(runtime_path)
        if index >= 0:
            self.combo_runtime.setCurrentIndex(index)

        target = options.get('target', 'desktop')
        index = self.combo_target.findData(target)
        if index >= 0:
            self.combo_target.setCurrentIndex(index)
        self.txt_custom_dir.setText(
            options.get('custom_dir', '')
            or options.get('desktop_dir', '')
            or self.generator.desktop_dir
        )

        filename = options.get('filename', '')
        if filename:
            self.txt_filename.setText(filename)
        else:
            self.txt_filename.setText(sanitize_filename(options.get('name', '')) + '.desktop')

        env_vars = options.get('env_vars') or {}
        if env_vars:
            summary = ', '.join(f'{key}={value}' for key, value in env_vars.items())
            self.lbl_env.setText(self.translator('desktop_env_note') + ' ' + summary)
        else:
            self.lbl_env.setText(self.translator('desktop_env_note_none'))

        self.on_target_changed()
        self._updating = False

    def get_options(self):
        return {
            'name': self.txt_name.text().strip(),
            'comment': self.txt_comment.text().strip(),
            'exe_path': self.txt_exe.text().strip(),
            'working_dir': self.txt_working_dir.text().strip(),
            'runtime_path': self.combo_runtime.currentData() or '',
            'icon_path': self.txt_icon.text().strip(),
            'args': self.txt_args.text().strip(),
            'categories': self.txt_categories.text().strip() or 'Game;',
            'terminal': self.chk_terminal.isChecked(),
            'target': self.combo_target.currentData() or 'desktop',
            'desktop_dir': self.txt_custom_dir.text().strip(),
            'filename': self.txt_filename.text().strip(),
            'app_id': self._app_id,
            'compat_data_path': self._compat_data_path,
        }

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------
    def on_name_changed(self, text):
        if self._updating:
            return
        if not self._filename_edited:
            self.txt_filename.setText(sanitize_filename(text) + '.desktop')
        if not self.txt_comment.text().strip():
            self.txt_comment.setText(text)
        self.update_preview()

    def on_filename_edited(self, _text):
        self._filename_edited = True

    def on_target_changed(self, *_args):
        custom = self.combo_target.currentData() == 'custom'
        self.txt_custom_dir.setEnabled(custom)
        self.btn_browse_target.setEnabled(custom)
        self.update_preview()

    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('select_exe'),
            self.txt_exe.text() or '',
            f"{self.translator('exe_files')} (*.exe);;{self.translator('all_files')} (*)"
        )
        if file_path:
            self.txt_exe.setText(file_path)
            if not self.txt_name.text().strip():
                self.txt_name.setText(os.path.splitext(os.path.basename(file_path))[0])
            # Keep the working directory in sync with the executable.
            self.txt_working_dir.setText(os.path.dirname(file_path))

    def browse_working_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('select_directory'),
            self.txt_working_dir.text() or ''
        )
        if directory:
            self.txt_working_dir.setText(directory)

    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translator('desktop_choose_icon'),
            self.txt_icon.text() or '',
            'Images (*.png *.jpg *.jpeg *.svg *.ico *.xpm);;All Files (*)'
        )
        if file_path:
            self.txt_icon.setText(file_path)

    def use_emoji_icon(self):
        icon_path = self.generator.default_icon_path
        if icon_path:
            self.txt_icon.setText(icon_path)
        else:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('desktop_icon_failed')
            )

    def extract_icon(self):
        exe_path = self.txt_exe.text().strip()
        if not exe_path or not os.path.isfile(exe_path):
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('exe_not_found')
            )
            return
        if self.icon_extractor is None:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('icon_tool_unavailable')
            )
            return
        if not self.icon_extractor.is_tool_available():
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('icon_tool_unavailable')
            )
            return

        progress = QProgressDialog(
            self.translator('extracting_icon'), None, 0, 0, self
        )
        progress.setWindowTitle(self.translator('please_wait'))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()

        task = IconExtractTask(self.icon_extractor, exe_path, self)
        self._icon_tasks.append(task)

        def done(icon_path, error):
            progress.close()
            progress.deleteLater()
            if task in self._icon_tasks:
                self._icon_tasks.remove(task)
            task.deleteLater()
            if icon_path:
                self.txt_icon.setText(icon_path)
            else:
                QMessageBox.warning(
                    self, self.translator('warning'),
                    error or self.translator('desktop_icon_failed')
                )

        task.extracted.connect(done)
        task.start()

    def browse_target_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            self.translator('desktop_custom_dir'),
            self.txt_custom_dir.text() or ''
        )
        if directory:
            self.txt_custom_dir.setText(directory)

    # ------------------------------------------------------------------
    # Preview / validation
    # ------------------------------------------------------------------
    def update_preview(self):
        if self._updating:
            return
        options = self.get_options()
        validation = self.generator.validate_options(
            name=options['name'],
            exe_path=options['exe_path'],
            working_dir=options['working_dir'],
            runtime_path=options['runtime_path'],
            icon_path=options['icon_path'],
            terminal=options['terminal'],
            target=options['target'],
            desktop_dir=options['desktop_dir'],
            filename=options['filename'],
            translator=self.translator,
        )

        messages = list(validation['errors']) + list(validation['warnings'])
        self.lbl_status.setText('\n'.join(messages))
        self.lbl_status.setStyleSheet(
            "color: #f44336; font-size: 11px;" if validation['errors']
            else "color: #ff9800; font-size: 11px;"
        )

        try:
            content = self.generator.build_desktop_content(
                name=options['name'],
                exe_path=options['exe_path'],
                icon_path=options['icon_path'],
                working_dir=options['working_dir'],
                runtime_path=options['runtime_path'],
                env_vars=self._base_env_vars,
                args=options['args'],
                comment=options['comment'],
                terminal=options['terminal'],
                categories=options['categories'],
                wine_options=self._wine_options,
                app_id=options.get('app_id', ''),
                compat_data_path=options.get('compat_data_path', ''),
            )
            self.preview.setPlainText(content)
        except Exception as exc:
            self.preview.setPlainText(
                self.translator('desktop_preview_unavailable').format(error=exc)
            )

    def validate_and_accept(self):
        options = self.get_options()
        validation = self.generator.validate_options(
            name=options['name'],
            exe_path=options['exe_path'],
            working_dir=options['working_dir'],
            runtime_path=options['runtime_path'],
            icon_path=options['icon_path'],
            terminal=options['terminal'],
            target=options['target'],
            desktop_dir=options['desktop_dir'],
            filename=options['filename'],
            translator=self.translator,
        )
        if validation['errors']:
            QMessageBox.warning(
                self, self.translator('warning'),
                '\n'.join(validation['errors'])
            )
            return

        target_dir = self.generator.resolve_target_dir(
            options['target'], options['desktop_dir']
        )
        filename = sanitize_filename(
            os.path.splitext(os.path.basename(options['filename'] or options['name']))[0]
        ) + '.desktop'
        full_path = os.path.join(target_dir, filename)
        if os.path.exists(full_path):
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowTitle(self.translator('warning'))
            box.setText(self.translator('desktop_overwrite_msg'))
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            box.button(QMessageBox.StandardButton.Yes).setText(
                self.translator('yes')
            )
            box.button(QMessageBox.StandardButton.No).setText(
                self.translator('no')
            )
            if box.exec() != QMessageBox.StandardButton.Yes:
                return

        if validation['warnings']:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle(self.translator('info'))
            box.setText('\n'.join(validation['warnings']))
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.button(QMessageBox.StandardButton.Ok).setText(
                self.translator('ok')
            )
            box.exec()

        self.accept()

    @property
    def _base_env_vars(self):
        return getattr(self, '_env_vars', {})

    @property
    def _wine_options(self):
        return getattr(self, '_wine_opts', {})

    def set_runtime_context(self, env_vars=None, wine_options=None,
                            compat_data_path=''):
        """Set environment variables and Wine options used for the preview."""
        self._env_vars = env_vars or {}
        self._wine_opts = wine_options or {}
        if compat_data_path:
            self._compat_data_path = compat_data_path
        self.update_preview()
