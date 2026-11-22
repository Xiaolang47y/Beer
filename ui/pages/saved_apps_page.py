# -*- coding: utf-8 -*-
"""Steam-style library page for saved applications."""

import datetime
import os
import shlex
import time

from PyQt6.QtCore import QProcess, QTimer, Qt
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMenu, QMessageBox,
    QProgressDialog, QStackedWidget, QWidget,
)

from core.desktop_generator import (
    DesktopGenerator,
    get_default_icon_path,
    sanitize_filename,
)
from core.desktop_importer import parse_desktop_file
from core.icon_extractor import IconExtractor
from core.runtime_utils import (
    app_prefix_info,
    detect_runtime,
    ensure_app_prefix_fields,
)
from ui.dialogs.common_dialogs import RuntimeSelectDialog, SimpleInputDialog
from ui.dialogs.desktop_dialog import DesktopEntryDialog
from ui.icon_extract_task import IconExtractTask
from ui.pages.app_detail_view import AppDetailView
from ui.pages.app_helpers import (
    app_category_keys,
    app_runtime_label,
    prepare_app_prefix,
)
from ui.pages.app_sidebar import AppSidebar, CategoryPanel
from ui.pages.shelf_view import ShelfView


class SavedAppsPage(QWidget):
    """Library page with shelves, category filters and an app detail view."""

    def __init__(self, config, translator, main_window):
        super().__init__()
        self.config = config
        self.translator = translator
        self.main_window = main_window

        self.apps = []
        self._search_text = ''
        self._categories = set()
        self._current_app_name = ''
        self._sort_mode = self.config.get('sort_mode', 'name')
        self._icon_tasks = []
        self._native_processes = []

        # Debounce search so typing does not rebuild every card immediately.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self._refresh_all)

        self._icon_extractor = IconExtractor(
            icons_dir=self.config.get_icons_dir()
            if hasattr(self.config, 'get_icons_dir') else None
        )

        self._build_ui()
        self._connect_signals()
        self.load_apps()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = AppSidebar(self.translator)
        layout.addWidget(self.sidebar)

        self.category_panel = CategoryPanel(self.translator)
        self.category_panel.hide()
        layout.addWidget(self.category_panel)

        self.stack = QStackedWidget()
        self._create_stack_pages()
        layout.addWidget(self.stack, 1)

        self.sidebar_menu = QMenu(self)
        self.sidebar_menu.addAction(
            self.translator('import'), self.import_apps
        )
        self.sidebar_menu.addAction(
            self.translator('export'), self.export_apps
        )
        self.sidebar.menu_button.setMenu(self.sidebar_menu)

    def _create_stack_pages(self):
        self.shelf_view = ShelfView(self)
        self.detail_view = AppDetailView(self)
        self.stack.addWidget(self.shelf_view)
        self.stack.addWidget(self.detail_view)
        self.stack.setCurrentWidget(self.shelf_view)

    def _connect_signals(self):
        self.sidebar.shelf_requested.connect(self.show_shelf)
        self.sidebar.search_changed.connect(self._on_search_changed)
        self.sidebar.filter_toggled.connect(self._on_filter_toggled)
        self.sidebar.app_activated.connect(self._open_app_by_name)
        self.sidebar.app_context_requested.connect(self._open_program_list_menu)
        self.sidebar.create_requested.connect(self._create_on_main_page)
        self.sidebar.import_desktop_requested.connect(self.import_desktop_file)
        self.category_panel.filter_changed.connect(self._on_category_filter)
        self.category_panel.sort_changed.connect(self._on_sort_changed)
        self.category_panel.set_sort_mode(self._sort_mode)

        log_signal = getattr(self.main_window, 'log_emitted', None)
        if log_signal is not None:
            log_signal.connect(self._on_log)

    def _on_log(self, message, level='info'):
        if hasattr(self, 'detail_view'):
            self.detail_view.append_log(message, level)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def load_apps(self):
        """Reload applications from disk and refresh every view."""
        self.apps = self.config.get_apps()
        self._refresh_all()

    def _refresh_all(self):
        filtered = self._filtered_apps()
        self.sidebar.set_apps(filtered)
        self.category_panel.set_apps(self.apps)
        self.shelf_view.set_data(self.config.get_shelves(), filtered)

        if self._current_app_name:
            self.sidebar.select_app(self._current_app_name)

    def _filtered_apps(self):
        search = self._search_text.strip().lower()
        result = []
        runtimes = self.get_runtimes()
        for app in self.apps:
            if self._categories:
                if not (app_category_keys(app) & self._categories):
                    continue
            if search:
                haystack = ' '.join([
                    app.get('name', ''),
                    app.get('description', ''),
                    app.get('exe_path', ''),
                    app.get('exec_cmd', ''),
                    app_runtime_label(app, self.translator, runtimes),
                ]).lower()
                if search not in haystack:
                    continue
            result.append(app)

        if self._sort_mode == 'runtime':
            result.sort(
                key=lambda app: int(app.get('total_runtime', 0) or 0),
                reverse=True,
            )
        elif self._sort_mode == 'import':
            result.sort(
                key=lambda app: app.get('created_at', '') or '',
                reverse=True,
            )
        else:
            result.sort(key=lambda app: app.get('name', '').casefold())
        return result

    def _find_app(self, name):
        for app in self.apps:
            if app.get('name') == name:
                return app
        return None

    def get_runtimes(self):
        manager = getattr(self.main_window.main_page, 'proton_manager', None)
        return manager.get_runtimes() if manager else []

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def show_shelf(self):
        self._current_app_name = ''
        if hasattr(self, 'detail_view'):
            self.detail_view.hero.set_edit_mode(None)
        self._refresh_all()
        self.stack.setCurrentWidget(self.shelf_view)
        self.sidebar.select_app('')

    def open_detail(self, app):
        if app is None:
            return
        self._current_app_name = app.get('name', '')
        self.detail_view.set_app(app)
        self.stack.setCurrentWidget(self.detail_view)
        self.sidebar.select_app(self._current_app_name)

    def _open_app_by_name(self, name):
        app = self._find_app(name)
        if app is not None:
            self.open_detail(app)

    def _on_search_changed(self, text):
        self._search_text = text or ''
        self._search_timer.start()

    def _on_filter_toggled(self, checked):
        self.category_panel.setVisible(bool(checked))

    def _on_category_filter(self, categories):
        self._categories = set(categories or ())
        self._refresh_all()

    def _on_sort_changed(self, mode):
        self._sort_mode = mode or 'name'
        self.config.set('sort_mode', self._sort_mode)
        self._refresh_all()

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------
    def update_app_field(self, app, key, value, refresh=True):
        """Persist a single field and optionally refresh the views."""
        app[key] = value
        self.config._save_apps()
        if refresh:
            self._refresh_all()
            if self.detail_view.app is app:
                if key == 'name':
                    self.detail_view.txt_name.setText(value)
                    self.detail_view.hero.update()
                self.detail_view.update_stats()

    def rename_app(self, app, new_name):
        """Rename an application, ensuring the name stays unique."""
        new_name = (new_name or '').strip()
        if not new_name:
            return False
        if new_name == app.get('name'):
            return True
        for other in self.apps:
            if other is not app and other.get('name') == new_name:
                QMessageBox.warning(
                    self, self.translator('warning'),
                    self.translator('name_exists')
                )
                return False

        old_name = app.get('name', '')
        app['name'] = new_name
        self.config._save_apps()
        if self._current_app_name == old_name:
            self._current_app_name = new_name
        self._refresh_all()
        if self.detail_view.app is app:
            self.detail_view.hero.update()
            self.detail_view.txt_name.setText(new_name)
        self.main_window.log_message(
            f"Renamed: {old_name} -> {new_name}", 'info'
        )
        return True

    def rename_app_dialog(self, app):
        dialog = SimpleInputDialog(
            self.translator('edit_name'), app.get('name', ''),
            self.translator, self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rename_app(app, dialog.get_text())

    def edit_description(self, app):
        dialog = SimpleInputDialog(
            self.translator('edit_desc'), app.get('description', ''),
            self.translator, self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_app_field(app, 'description', dialog.get_text().strip())

    def change_runtime(self, app):
        dialog = RuntimeSelectDialog(
            app.get('proton_path', ''), self.get_runtimes(),
            self.translator, self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        path = dialog.get_runtime_path()
        if not path:
            return

        runtime = detect_runtime(path)
        if runtime is None:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('runtime_invalid')
            )
            return

        self._remember_custom_path(runtime.get('path', ''))
        app['native'] = False
        app['proton_path'] = path
        app['runtime_type'] = runtime.get('type', '')
        ensure_app_prefix_fields(self.config, app)
        self.config._save_apps()
        self._refresh_all()
        if self.detail_view.app is app:
            self.detail_view.set_app(app)
        self.main_window.log_message(
            f"Runtime updated for {app.get('name', '')}: {path}", 'info'
        )

    def _remember_custom_path(self, path):
        if not path:
            return
        known = {
            os.path.realpath(item.get('path', ''))
            for item in self.get_runtimes()
        }
        custom_paths = list(self.config.get('custom_proton_paths', []))
        real = os.path.realpath(path)
        if real in known or any(os.path.realpath(p) == real for p in custom_paths):
            return
        custom_paths.append(path)
        self.config.set('custom_proton_paths', custom_paths)
        main_page = getattr(self.main_window, 'main_page', None)
        if main_page and main_page.proton_manager:
            main_page.load_proton_versions()

    # ------------------------------------------------------------------
    # Shelves
    # ------------------------------------------------------------------
    def create_shelf(self):
        dialog = SimpleInputDialog(
            self.translator('add_shelf'), '', self.translator, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_text().strip()
            if name:
                self.config.add_shelf(name)
                self._refresh_all()

    def rename_shelf(self, shelf):
        dialog = SimpleInputDialog(
            self.translator('shelf_rename'),
            shelf.get('name', ''),
            self.translator,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_text().strip()
            if name:
                self.config.rename_shelf(shelf.get('id'), name)
                self._refresh_all()

    def move_shelf(self, shelf, delta):
        if self.config.move_shelf(shelf.get('id'), delta):
            self._refresh_all()

    def delete_shelf(self, shelf):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self.translator('warning'))
        box.setText(self.translator('shelf_delete_msg').format(
            name=shelf.get('name', '')
        ))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.button(QMessageBox.StandardButton.Yes).setText(self.translator('yes'))
        box.button(QMessageBox.StandardButton.No).setText(self.translator('no'))
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.config.delete_shelf(shelf.get('id'))
            self._refresh_all()

    def set_shelf_collapsed(self, shelf, collapsed):
        """Persist the collapsed state of a shelf."""
        shelf_id = shelf.get('id')
        if not shelf_id:
            return
        shelf['collapsed'] = bool(collapsed)
        shelves = self.config.get_shelves()
        for item in shelves:
            if item.get('id') == shelf_id:
                item['collapsed'] = bool(collapsed)
                break
        self.config.save_shelves(shelves)

    def assign_apps_to_shelf(self, names, shelf_id):
        if not shelf_id:
            return
        names = set(names or [])
        changed = False
        for app in self.apps:
            if app.get('name') not in names:
                continue
            memberships = list(app.get('shelves') or [])
            if shelf_id not in memberships:
                memberships.append(shelf_id)
                app['shelves'] = memberships
                changed = True
        if changed:
            self.config._save_apps()
            self._refresh_all()

    # ------------------------------------------------------------------
    # Add / import
    # ------------------------------------------------------------------
    def _create_on_main_page(self):
        self.main_window.show_page(0)

    def import_desktop_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, self.translator('import_desktop'),
            os.path.expanduser('~/.local/share/applications'),
            'Desktop Entry (*.desktop);;All Files (*)',
        )
        if not paths:
            return

        imported = []
        failures = []
        for path in paths:
            try:
                app = parse_desktop_file(path)
                if not isinstance(app, dict):
                    raise ValueError('Invalid desktop entry')
            except Exception as exc:
                failures.append((os.path.basename(path), str(exc)))
                continue
            app['name'] = self._unique_name(app.get('name', 'Imported'))
            self.config.save_app(app)
            self.apps = self.config.get_apps()
            imported.append(app)
            self.main_window.log_message(
                self.translator('desktop_import_success').format(
                    name=app.get('name', '')
                ),
                'success',
            )

        for filename, error in failures:
            self.main_window.log_message(
                self.translator('desktop_import_failed').format(
                    error=f'{filename}: {error}'
                ),
                'error',
            )

        self.load_apps()
        if len(imported) == 1 and not failures:
            self.open_detail(imported[0])
            return

        if failures:
            message = self.translator(
                'desktop_import_failed_count'
            ).format(count=len(failures))
            if imported:
                message += '\n' + self.translator(
                    'desktop_import_count'
                ).format(count=len(imported))
            QMessageBox.warning(
                self, self.translator('warning'), message
            )
        elif imported:
            QMessageBox.information(
                self, self.translator('success'),
                self.translator('desktop_import_count').format(
                    count=len(imported)
                ),
            )

    def _unique_name(self, base):
        return self.config.unique_app_name(base or 'Imported')

    def import_apps(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.translator('import'), '',
            'JSON Files (*.json);;All Files (*)',
        )
        if file_path:
            if self.config.import_apps(file_path):
                self.load_apps()
                self.main_window.log_message('Applications imported', 'success')
            else:
                QMessageBox.warning(
                    self, self.translator('error'),
                    'Failed to import applications'
                )

    def export_apps(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.translator('export'), '',
            'JSON Files (*.json);;All Files (*)',
        )
        if file_path:
            if self.config.export_apps(file_path):
                self.main_window.log_message('Applications exported', 'success')
            else:
                QMessageBox.warning(
                    self, self.translator('error'),
                    'Failed to export applications'
                )

    # ------------------------------------------------------------------
    # Launching
    # ------------------------------------------------------------------
    def launch_app(self, app):
        """Launch a saved application and track its runtime."""
        if app is None:
            return
        if app.get('native'):
            self._launch_native(app)
        else:
            self._launch_windows(app)

    def _launch_native(self, app):
        command = app.get('exec_cmd') or app.get('exe_path', '')
        try:
            argv = shlex.split(command)
        except ValueError:
            argv = [command]
        if not argv:
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('file_not_found')
            )
            return

        working_dir = app.get('run_directory', '') or os.path.dirname(argv[0])
        process = QProcess(self)
        if working_dir and os.path.isdir(working_dir):
            process.setWorkingDirectory(working_dir)

        def on_output(is_stderr):
            data = (
                process.readAllStandardError() if is_stderr
                else process.readAllStandardOutput()
            )
            text = bytes(data).decode('utf-8', errors='replace')
            if text:
                self.main_window.log_message(text, 'proton' if is_stderr else 'info')

        process.readyReadStandardOutput.connect(lambda: on_output(False))
        process.readyReadStandardError.connect(lambda: on_output(True))

        started = time.time()
        process.finished.connect(
            lambda code, status, a=app, s=started, p=process:
            self._finish_native(a, s, code, p)
        )
        self._native_processes.append(process)
        process.start(argv[0], argv[1:])
        if not process.waitForStarted(5000):
            self._native_processes.remove(process)
            process.deleteLater()
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('launch_failed')
            )
            return

        self._mark_launch(app)
        self.main_window.log_message(
            '{}: {}'.format(self.translator('launching'), app.get('name', '')),
            'info',
        )

    def _finish_native(self, app, started, exit_code, process):
        if process in self._native_processes:
            self._native_processes.remove(process)
        process.deleteLater()
        self._record_runtime(app, started)
        self.main_window.log_message(
            '{}: {}'.format(self.translator('process_ended'), exit_code),
            'success' if exit_code == 0 else 'error',
        )

    def _launch_windows(self, app):
        exe_path = app.get('exe_path', '')
        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('exe_not_found')
            )
            return

        manager = getattr(self.main_window.main_page, 'proton_manager', None)
        if manager is None:
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('runtime_missing')
            )
            return

        runtime_path = app.get('proton_path', '')
        runtime = manager.get_runtime_by_path(runtime_path)
        if runtime is None:
            runtimes = manager.get_runtimes()
            runtime = runtimes[0] if runtimes else None
        if runtime is None:
            QMessageBox.warning(
                self, self.translator('error'),
                self.translator('runtime_select_first')
            )
            return

        prepared = prepare_app_prefix(
            self, self.config, app, self.translator
        )
        if prepared is None:
            return
        prefix_type, prefix_path = prepared

        env_vars = self.config.get('environment_variables', {})
        more_options = app.get('more_options', {}) or {}
        args_text = more_options.get('startup_args', '') or ''
        try:
            args = shlex.split(args_text) if args_text.strip() else None
        except ValueError:
            args = args_text.split()
        wine_options = dict(more_options.get('wine_options', {}) or {})
        compat_data_path = None
        if prefix_type == 'proton':
            compat_data_path = prefix_path
        elif prefix_type == 'wine' and not wine_options.get('prefix'):
            wine_options['prefix'] = prefix_path

        if self.config.get('show_log_on_start', False):
            self.main_window.show_log()

        success, result = manager.launch_program(
            runtime.get('path', ''), exe_path,
            app.get('run_directory', '') or os.path.dirname(exe_path),
            env_vars, args,
            output_callback=self.main_window.log_message,
            wine_options=wine_options,
            architecture=app.get('architecture', 'auto'),
            compat_data_path=compat_data_path,
        )

        if not success:
            self.main_window.log_message(
                '{}: {}'.format(self.translator('launch_failed'), result),
                'error',
            )
            return

        started = time.time()
        result.finished.connect(
            lambda code, status, a=app, s=started: self._record_runtime(a, s)
        )
        self._mark_launch(app)
        self.main_window.log_message(
            '{}: {}'.format(self.translator('launching'), app.get('name', '')),
            'info',
        )

    def _mark_launch(self, app):
        app['last_launched'] = datetime.datetime.now().isoformat(
            timespec='seconds'
        )
        self.config._save_apps()
        # Keep shelf cards and the sidebar in sync immediately.
        self._refresh_all()
        if self.detail_view.app is app:
            self.detail_view.update_stats()

    def _record_runtime(self, app, started):
        elapsed = max(0, int(time.time() - started))
        app['total_runtime'] = int(app.get('total_runtime', 0) or 0) + elapsed
        self.config._save_apps()
        # Update the visible "Played" label without leaving the page.
        self._refresh_all()
        if self.detail_view.app is app:
            self.detail_view.update_stats()

    def stop_native_processes(self):
        """Terminate all running native Linux applications."""
        stopped = 0
        for process in list(self._native_processes):
            try:
                if process.state() == QProcess.ProcessState.NotRunning:
                    continue
                process.terminate()
                if not process.waitForFinished(1500):
                    process.kill()
                    process.waitForFinished(1000)
                stopped += 1
            except Exception:
                continue
        return stopped

    # ------------------------------------------------------------------
    # Context menu / shortcuts
    # ------------------------------------------------------------------
    def show_context_menu(self, global_pos, app, source_widget, shelf=None):
        menu = QMenu(self)
        menu.addAction(
            self.translator('run'), lambda: self.launch_app(app)
        )
        menu.addAction(
            self.translator('add_shortcut'),
            lambda: self.add_desktop_shortcut(app),
        )
        menu.addAction(
            self.translator('edit'), lambda: self.open_detail(app)
        )
        if shelf and not shelf.get('preset') and shelf.get('id'):
            menu.addSeparator()
            menu.addAction(
                self.translator('shelf_remove_app'),
                lambda: self.remove_from_shelf(app, shelf.get('id')),
            )
        menu.addSeparator()
        menu.addAction(
            self.translator('delete'), lambda: self.delete_app(app)
        )
        menu.exec(global_pos)

    def _open_program_list_menu(self, app_names, global_pos):
        if isinstance(app_names, str):
            app_names = [app_names]
        apps = [
            app for app in (self._find_app(name) for name in app_names)
            if app is not None
        ]
        if not apps:
            return
        menu = QMenu(self)
        if len(apps) == 1:
            app = apps[0]
            menu.addAction(
                self.translator('run'), lambda: self.launch_app(app)
            )
            menu.addAction(
                self.translator('edit'), lambda: self.open_detail(app)
            )
            menu.addAction(
                self.translator('add_shortcut'),
                lambda: self.add_desktop_shortcut(app),
            )
            menu.addSeparator()
            menu.addAction(
                self.translator('delete'), lambda: self.delete_apps([app])
            )
        else:
            menu.addAction(
                self.translator('delete_selected').format(count=len(apps)),
                lambda: self.delete_apps(apps),
            )
        menu.exec(global_pos)

    def remove_from_shelf(self, app, shelf_id):
        """Remove an application from a custom shelf without deleting it."""
        memberships = list(app.get('shelves') or [])
        if shelf_id not in memberships:
            return
        app['shelves'] = [item for item in memberships if item != shelf_id]
        self.config._save_apps()
        self._refresh_all()
        self.main_window.log_message(
            self.translator('shelf_app_removed').format(
                name=app.get('name', '')
            ),
            'info',
        )

    def delete_app(self, app):
        self.delete_apps([app])

    def delete_apps(self, apps):
        apps = [app for app in (apps or []) if app is not None]
        if not apps:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(self.translator('confirm_delete'))
        if len(apps) == 1:
            box.setText(self.translator('confirm_delete_msg'))
        else:
            box.setText(
                self.translator('confirm_delete_multi_msg').format(
                    count=len(apps)
                )
            )
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.button(QMessageBox.StandardButton.Yes).setText(self.translator('yes'))
        box.button(QMessageBox.StandardButton.No).setText(self.translator('no'))
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        names = [app.get('name', '') for app in apps]
        if self._current_app_name in names:
            self.show_shelf()
        self.config.delete_apps(names)
        self.load_apps()
        if len(apps) == 1:
            self.main_window.log_message(
                f"Deleted: {names[0]}", 'info'
            )
        else:
            self.main_window.log_message(
                self.translator('deleted_count').format(count=len(names)),
                'info',
            )

    def add_desktop_shortcut(self, app):
        """Generate a desktop shortcut, extracting the icon in the background."""
        name = app.get('name', '')
        exe_path = app.get('exe_path', '')
        if not name or not exe_path:
            QMessageBox.warning(
                self, self.translator('warning'),
                self.translator('desktop_name_exe_required')
            )
            return

        icon_path = app.get('icon_path', '')
        if icon_path and os.path.exists(icon_path):
            self._open_shortcut_dialog(app, icon_path)
            return
        if self._icon_extractor.is_tool_available():
            self._extract_shortcut_icon_async(app)
        else:
            self._open_shortcut_dialog(app, get_default_icon_path())

    def _extract_shortcut_icon_async(self, app):
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

        task = IconExtractTask(
            self._icon_extractor, app.get('exe_path', ''), self
        )
        self._icon_tasks.append(task)

        def done(icon_path, error):
            progress.close()
            progress.deleteLater()
            if task in self._icon_tasks:
                self._icon_tasks.remove(task)
            task.deleteLater()
            if error:
                self.main_window.log_message(
                    '{}: {}'.format(
                        self.translator('icon_extraction_failed'), error
                    ),
                    'warning',
                )
            self._open_shortcut_dialog(
                app, icon_path or get_default_icon_path()
            )

        task.extracted.connect(done)
        task.start()

    def _open_shortcut_dialog(self, app, icon_path=''):
        name = app.get('name', '')
        description = app.get('description', '')
        more_options = app.get('more_options', {}) or {}
        args_text = more_options.get('startup_args', '') or ''

        prefix_type, prefix_path, _legacy = app_prefix_info(
            self.config, app
        )
        wine_options = dict(more_options.get('wine_options', {}) or {})
        if prefix_type == 'wine' and not wine_options.get('prefix'):
            wine_options['prefix'] = prefix_path
        compat_data_path = prefix_path if prefix_type == 'proton' else ''

        options = {
            'name': name,
            'comment': description or name,
            'exe_path': app.get('exe_path', ''),
            'working_dir': app.get('run_directory', ''),
            'runtime_path': app.get('proton_path', ''),
            'icon_path': icon_path,
            'args': args_text,
            'categories': 'Game;',
            'terminal': False,
            'target': 'desktop',
            'filename': sanitize_filename(name) + '.desktop',
            'app_id': app.get('app_id', ''),
            'compat_data_path': compat_data_path,
        }

        dialog = DesktopEntryDialog(
            options,
            self.translator,
            runtimes=self.get_runtimes(),
            icon_extractor=self._icon_extractor,
            parent=self,
        )
        dialog.set_runtime_context(
            env_vars=self.config.get('environment_variables', {}),
            wine_options=wine_options,
            compat_data_path=compat_data_path,
        )
        if not dialog.exec():
            return

        desktop_options = dialog.get_options()
        generator = DesktopGenerator()
        success, result = generator.generate_desktop_file(
            **desktop_options,
            env_vars=self.config.get('environment_variables', {}),
            wine_options=wine_options,
            translator=self.translator,
        )

        if success:
            app['desktop_options'] = desktop_options
            self.config._save_apps()
            self.main_window.log_message(
                '{}: {}'.format(
                    self.translator('desktop_file_generated'), result
                ),
                'success',
            )
            QMessageBox.information(
                self, self.translator('success'),
                '{}\n{}'.format(
                    self.translator('desktop_file_generated'), result
                ),
            )
        else:
            self.main_window.log_message(
                '{}: {}'.format(
                    self.translator('desktop_generation_failed'), result
                ),
                'error',
            )
            QMessageBox.warning(
                self, self.translator('error'),
                '{}\n{}'.format(
                    self.translator('desktop_generation_failed'), result
                ),
            )

    # ------------------------------------------------------------------
    # Refresh / i18n
    # ------------------------------------------------------------------
    def refresh(self):
        """Reload data and retranslate the whole page."""
        self.sidebar.update_texts()
        self.category_panel.update_texts()
        self.sidebar_menu.clear()
        self.sidebar_menu.addAction(
            self.translator('import'), self.import_apps
        )
        self.sidebar_menu.addAction(
            self.translator('export'), self.export_apps
        )

        # Recreate the views so every static label uses the new language.
        for index in range(self.stack.count() - 1, -1, -1):
            widget = self.stack.widget(index)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self._create_stack_pages()
        self.category_panel.clear_selection()
        self._categories = set()
        self._current_app_name = ''
        self.load_apps()
