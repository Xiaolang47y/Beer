# -*- coding: utf-8 -*-
"""
Proton version manager for Beer
"""

import os
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class ProtonManager(QObject):
    """Manages Proton installations"""

    def __init__(self, search_paths=None):
        super().__init__()
        self.search_paths = search_paths or [
            os.path.expanduser('~/.steam/steam/steamapps/common/'),
            os.path.expanduser('~/.local/share/Steam/steamapps/common/')
        ]
        self.proton_versions = []
        # Keep references to running processes so they aren't garbage-collected
        self._processes = []
        self.scan_proton_versions()

    def scan_proton_versions(self):
        """Scan for installed Proton versions"""
        self.proton_versions = []

        for search_path in self.search_paths:
            if not os.path.exists(search_path):
                continue

            try:
                for item in os.listdir(search_path):
                    item_path = os.path.join(search_path, item)

                    if os.path.isdir(item_path) and item.startswith('Proton'):
                        proton_script = os.path.join(item_path, 'proton')

                        if os.path.exists(proton_script):
                            version = self._extract_version(item)
                            self.proton_versions.append({
                                'name': item,
                                'version': version,
                                'path': item_path,
                                'proton_script': proton_script
                            })
            except Exception as e:
                print(f"Error scanning {search_path}: {e}")

        # Sort by version
        self.proton_versions.sort(key=lambda x: x['version'], reverse=True)

    def _extract_version(self, name):
        """Extract version number from Proton directory name"""
        if name.startswith('Proton-'):
            name = name[7:]

        parts = name.split('.')
        version_parts = []

        for part in parts:
            num = ''
            for char in part:
                if char.isdigit():
                    num += char
                else:
                    break

            if num:
                version_parts.append(int(num))

        return tuple(version_parts) if version_parts else (0,)

    def get_proton_versions(self):
        """Get list of Proton versions"""
        return self.proton_versions

    def get_proton_by_name(self, name):
        """Get Proton by name"""
        for proton in self.proton_versions:
            if proton['name'] == name:
                return proton
        return None

    def validate_proton_path(self, path):
        """Validate if a path contains a valid Proton installation"""
        if not os.path.exists(path):
            return False

        proton_script = os.path.join(path, 'proton')
        return os.path.exists(proton_script)

    def get_steam_compat_paths(self, proton_path):
        """Get Steam compatibility paths for a Proton installation"""
        steam_paths = [
            os.path.expanduser('~/.steam/steam'),
            os.path.expanduser('~/.local/share/Steam')
        ]

        for steam_path in steam_paths:
            if os.path.exists(steam_path):
                return {
                    'STEAM_COMPAT_CLIENT_INSTALL_PATH': steam_path,
                    'STEAM_COMPAT_DATA_PATH': os.path.expanduser('~/.steam/steam/steamapps/compatdata/default')
                }

        return None

    def launch_program(self, proton_path, exe_path, working_dir=None,
                       env_vars=None, args=None, output_callback=None):
        """Launch a Windows program using Proton.

        Uses QProcess so Proton's stdout/stderr can be streamed to the log
        panel via ``output_callback``.

        Returns ``(success, process_or_error)``.
        """
        if not os.path.exists(exe_path):
            return False, "Executable not found"

        proton_script = os.path.join(proton_path, 'proton')
        if not os.path.exists(proton_script):
            return False, "Proton script not found"

        # Build environment
        env = os.environ.copy()

        compat_paths = self.get_steam_compat_paths(proton_path)
        if compat_paths:
            env.update(compat_paths)

        if env_vars:
            env.update(env_vars)

        # Build command arguments
        cmd = [proton_script, 'run', exe_path]
        if args:
            cmd.extend(args)

        cwd = working_dir or os.path.dirname(exe_path)

        try:
            process = QProcess()

            # Apply env vars to the process environment
            from PyQt6.QtCore import QProcessEnvironment
            proc_env = QProcessEnvironment.systemEnvironment()
            for key, value in env.items():
                proc_env.insert(key, str(value))
            process.setProcessEnvironment(proc_env)

            process.setWorkingDirectory(cwd)

            # Stream output if callback provided
            if output_callback:
                process.readyReadStandardOutput.connect(
                    lambda: self._read_output(process, output_callback, False)
                )
                process.readyReadStandardError.connect(
                    lambda: self._read_output(process, output_callback, True)
                )

            process.start(cmd[0], cmd[1:])

            if not process.waitForStarted(5000):
                return False, "Failed to start process"

            # Keep reference so it stays alive
            self._processes.append(process)

            # Clean up when finished
            process.finished.connect(
                lambda code, status, p=process: self._on_finished(p, code, output_callback)
            )

            return True, process
        except Exception as e:
            return False, str(e)

    def _read_output(self, process, callback, is_stderr):
        """Read available output from process and forward to callback"""
        try:
            if is_stderr:
                data = process.readAllStandardError()
            else:
                data = process.readAllStandardOutput()
            text = bytes(data).decode('utf-8', errors='replace').rstrip()
            if text:
                callback(text, 'proton')
        except Exception:
            pass

    def _on_finished(self, process, exit_code, callback):
        """Handle process completion"""
        try:
            if process in self._processes:
                self._processes.remove(process)
            if callback:
                callback(f"Process exited with code {exit_code}",
                         'success' if exit_code == 0 else 'error')
            process.deleteLater()
        except Exception:
            pass
