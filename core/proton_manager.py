# -*- coding: utf-8 -*-
"""
Proton / Wine runtime manager for Beer

The heavy lifting (scanning the filesystem, reading Wine versions) lives in
:mod:`core.runtime_utils`.  This class adds Qt process handling and keeps
references to running processes so their output can be streamed to the log
panel.
"""

import os
import shlex

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from core.runtime_utils import (
    apply_windows_version,
    build_runtime_environment,
    default_proton_search_paths,
    default_wine_search_paths,
    detect_runtime,
    expand_path,
    get_wine_arguments,
    runtime_key,
    wine_binary_for,
)


class ProtonManager(QObject):
    """Detects Proton/Wine runtimes and launches Windows programs."""

    runtimes_changed = pyqtSignal()

    def __init__(self, search_paths=None, wine_search_paths=None, custom_paths=None):
        super().__init__()
        self.search_paths = [expand_path(p) for p in (search_paths or []) if p]
        self.wine_search_paths = [expand_path(p) for p in (wine_search_paths or []) if p]
        self.custom_paths = [expand_path(p) for p in (custom_paths or []) if p]

        if not self.search_paths:
            self.search_paths = default_proton_search_paths()
        if not self.wine_search_paths:
            self.wine_search_paths = default_wine_search_paths()

        self.proton_versions = []
        self._processes = []
        self._output_buffers = {}
        self.scan_proton_versions()

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------
    def update_paths(self, search_paths=None, wine_search_paths=None,
                     custom_paths=None):
        """Update search paths and rescan."""
        if search_paths is not None:
            self.search_paths = [expand_path(p) for p in search_paths if p]
            if not self.search_paths:
                self.search_paths = default_proton_search_paths()
        if wine_search_paths is not None:
            self.wine_search_paths = [expand_path(p) for p in wine_search_paths if p]
            if not self.wine_search_paths:
                self.wine_search_paths = default_wine_search_paths()
        if custom_paths is not None:
            self.custom_paths = [expand_path(p) for p in custom_paths if p]
        self.scan_proton_versions()

    def scan_proton_versions(self):
        """Scan default, configured and custom paths for runtimes."""
        self.proton_versions = []
        seen = {}

        def add(entry, custom_root=''):
            if not entry:
                return
            key = runtime_key(entry)
            if key in seen:
                if custom_root:
                    seen[key]['custom'] = True
                    seen[key]['custom_root'] = custom_root
                return
            if custom_root:
                entry['custom'] = True
                entry['custom_root'] = custom_root
            seen[key] = entry
            self.proton_versions.append(entry)

        # Proton installations from Steam libraries.
        for search_path in self.search_paths:
            if not os.path.isdir(search_path):
                continue
            try:
                for item in sorted(os.listdir(search_path)):
                    item_path = os.path.join(search_path, item)
                    if not os.path.isdir(item_path):
                        continue
                    entry = detect_runtime(item_path, source='steam')
                    if entry and entry.get('type') == 'proton':
                        add(entry)
            except OSError as exc:
                print(f"Error scanning {search_path}: {exc}")

        # Wine installations from common locations.
        for search_path in self.wine_search_paths:
            if not os.path.isdir(search_path):
                continue
            try:
                for item in sorted(os.listdir(search_path)):
                    item_path = os.path.join(search_path, item)
                    if not os.path.isdir(item_path):
                        continue
                    entry = detect_runtime(item_path, source='system')
                    if entry and entry.get('type') == 'wine':
                        add(entry)
            except OSError as exc:
                print(f"Error scanning {search_path}: {exc}")

        # Wine binaries that are directly available in PATH.
        for name in ('wine', 'wine-stable', 'wine-staging', 'wine-devel', 'wine64'):
            import shutil
            binary = shutil.which(name)
            if binary:
                entry = detect_runtime(binary, source='system')
                if entry and entry.get('type') == 'wine':
                    add(entry)

        # Explicit custom paths.  They may point at a Proton directory,
        # a Wine installation directory or a Wine binary.
        for custom_path in self.custom_paths:
            entry = detect_runtime(custom_path, source='custom')
            if entry:
                add(entry, custom_root=expand_path(custom_path))

        # Proton first, then Wine; newest versions first inside each group.
        self.proton_versions.sort(
            key=lambda item: (
                0 if item.get('type') == 'proton' else 1,
                tuple(-n for n in item.get('version', ())),
            )
        )
        self.runtimes_changed.emit()

    def refresh(self):
        """Rescan and return the new runtime list."""
        self.scan_proton_versions()
        return self.proton_versions

    def get_runtimes(self):
        """Return every detected runtime (Proton and Wine)."""
        return list(self.proton_versions)

    def get_proton_versions(self):
        """Backward compatible alias returning Proton entries only."""
        return [runtime for runtime in self.proton_versions
                if runtime.get('type') == 'proton']

    def get_runtime_by_path(self, path):
        """Find a runtime by its ``path`` value."""
        path = expand_path(path)
        if not path:
            return None
        real = os.path.realpath(path)
        for runtime in self.proton_versions:
            if os.path.realpath(runtime.get('path', '')) == real:
                return runtime
        return None

    def get_proton_by_name(self, name):
        """Find a runtime by its display name."""
        for runtime in self.proton_versions:
            if runtime.get('name') == name:
                return runtime
        return None

    def validate_proton_path(self, path):
        """Return True when *path* contains a Proton or Wine installation."""
        return detect_runtime(path) is not None

    def is_custom_path(self, path):
        real = os.path.realpath(expand_path(path))
        return any(os.path.realpath(p) == real for p in self.custom_paths)

    # ------------------------------------------------------------------
    # Launching
    # ------------------------------------------------------------------
    def launch_program(self, proton_path, exe_path, working_dir=None,
                       env_vars=None, args=None, output_callback=None,
                       wine_options=None, architecture=None,
                       compat_data_path=None):
        """Launch a Windows program with Proton or Wine.

        Returns ``(success, process_or_error)``.
        """
        if not os.path.exists(exe_path):
            return False, "Executable not found"

        runtime = self.get_runtime_by_path(proton_path)
        if runtime is None:
            runtime = detect_runtime(proton_path)

        command = self.build_launch_command(runtime, exe_path, args, wine_options)
        if not command:
            return False, "Proton/Wine runtime not found"

        runtime_env, _prefix = build_runtime_environment(
            runtime, wine_options=wine_options, env_vars=env_vars,
            architecture=architecture, compat_data_path=compat_data_path
        )
        if compat_data_path and runtime and runtime.get('type') == 'proton':
            runtime_env['STEAM_COMPAT_DATA_PATH'] = expand_path(compat_data_path)
            try:
                os.makedirs(runtime_env['STEAM_COMPAT_DATA_PATH'], exist_ok=True)
            except OSError:
                pass

        # Apply the requested Windows version before launching.
        apply_windows_version(
            runtime, runtime_env, wine_options=wine_options,
            output_callback=output_callback
        )

        cwd = working_dir or os.path.dirname(exe_path)

        try:
            process = QProcess()

            proc_env = QProcessEnvironment.systemEnvironment()
            for key, value in runtime_env.items():
                proc_env.insert(str(key), str(value))
            process.setProcessEnvironment(proc_env)
            process.setWorkingDirectory(cwd)

            if output_callback:
                process.readyReadStandardOutput.connect(
                    lambda p=process: self._read_output(p, output_callback, False)
                )
                process.readyReadStandardError.connect(
                    lambda p=process: self._read_output(p, output_callback, True)
                )

            process.start(command[0], command[1:])

            if not process.waitForStarted(5000):
                return False, "Failed to start process"

            self._processes.append(process)
            process.finished.connect(
                lambda code, status, p=process: self._on_finished(p, code, output_callback)
            )

            if output_callback:
                output_callback(
                    'Command: ' + ' '.join(shlex.quote(part) for part in command),
                    'info'
                )

            return True, process
        except Exception as exc:
            return False, str(exc)

    def build_launch_command(self, runtime, exe_path, args=None, wine_options=None):
        """Build the argv list used to launch *exe_path*."""
        args = list(args or [])

        if runtime and runtime.get('type') == 'proton':
            proton_script = runtime.get('proton_script') or os.path.join(
                runtime.get('path', ''), 'proton'
            )
            if not os.path.isfile(proton_script):
                return None
            return [proton_script, 'run', exe_path] + args

        if runtime and runtime.get('type') == 'wine':
            wine_binary = runtime.get('wine_binary') or wine_binary_for(runtime)
            if not wine_binary:
                return None
            return [wine_binary] + get_wine_arguments(wine_options) + [exe_path] + args

        return [exe_path] + args

    # ------------------------------------------------------------------
    # Process output
    # ------------------------------------------------------------------
    def _read_output(self, process, callback, is_stderr):
        """Forward all available stdout/stderr to the log callback."""
        try:
            if is_stderr:
                data = process.readAllStandardError()
            else:
                data = process.readAllStandardOutput()
            text = bytes(data).decode('utf-8', errors='replace')
            if text:
                key = id(process)
                buffer_key = (key, 'err' if is_stderr else 'out')
                buffered = self._output_buffers.get(buffer_key, '') + text

                # Keep the tail after the last newline buffered so chunks of
                # a single line are not split (but never discard output).
                if '\n' in buffered:
                    complete, remainder = buffered.rsplit('\n', 1)
                    self._output_buffers[buffer_key] = remainder
                    if complete:
                        callback(complete + '\n', 'proton')
                else:
                    self._output_buffers[buffer_key] = buffered
        except Exception:
            pass

    def _flush_output(self, process, callback):
        for suffix in ('out', 'err'):
            key = (id(process), suffix)
            remainder = self._output_buffers.pop(key, '')
            if remainder:
                try:
                    callback(remainder, 'proton')
                except Exception:
                    pass

    def _on_finished(self, process, exit_code, callback):
        """Handle process completion."""
        try:
            if process in self._processes:
                self._processes.remove(process)
            if callback:
                self._flush_output(process, callback)
                callback(
                    f"Process exited with code {exit_code}",
                    'success' if exit_code == 0 else 'error'
                )
            process.deleteLater()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Force stop
    # ------------------------------------------------------------------
    def terminate_all(self):
        """Terminate every running Proton/Wine process.

        Returns the number of processes that were asked to stop.
        """
        stopped = 0
        for process in list(self._processes):
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
