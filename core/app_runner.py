# -*- coding: utf-8 -*-
"""Headless launcher used by generated shortcuts and the command line.

Launching through this module records the start time immediately and adds the
elapsed time to ``total_runtime`` when the program exits, even when the Beer
window is not running.
"""

import datetime
import os
import shlex
import signal
import subprocess
import sys
import time

from core.config_manager import ConfigManager
from core.runtime_utils import (
    app_prefix_info,
    apply_windows_version,
    build_runtime_environment,
    detect_runtime,
    get_wine_arguments,
    migrate_prefix,
    prefix_needs_migration,
    wine_binary_for,
)


def _log(message):
    line = '[{}] {}'.format(
        datetime.datetime.now().isoformat(timespec='seconds'), message
    )
    print(line, file=sys.stderr)
    try:
        path = os.path.expanduser('~/.local/share/Beer/runner.log')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(line + '\n')
    except OSError:
        pass


def _find_app(config, key):
    key = str(key or '')
    for app in config.get_apps():
        if app.get('app_id') == key:
            return app
    for app in config.get_apps():
        if app.get('name') == key:
            return app
    return None


def _update_app(app_id, callback):
    """Reload the app list, update one entry and save it."""
    config = ConfigManager()
    app = _find_app(config, app_id)
    if app is None:
        return False
    callback(app)
    return config._save_apps()


class _Session:
    def __init__(self, app_id):
        self.app_id = app_id
        self.started = time.time()
        self.recorded = False

    def mark_started(self):
        _update_app(self.app_id, lambda app: app.__setitem__(
            'last_launched',
            datetime.datetime.now().isoformat(timespec='seconds'),
        ))

    def record(self):
        if self.recorded:
            return
        self.recorded = True
        elapsed = max(0, int(time.time() - self.started))

        def apply(app):
            app['total_runtime'] = (
                int(app.get('total_runtime', 0) or 0) + elapsed
            )

        _update_app(self.app_id, apply)


_session = None


def _handle_signal(signum, _frame):
    if _session is not None:
        _session.record()
    raise SystemExit(128 + signum)


def _install_signal_handlers():
    for name in ('SIGTERM', 'SIGINT', 'SIGHUP'):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handle_signal)
        except (OSError, ValueError):
            pass


def _spawn(command, cwd=None, env=None):
    if not command:
        return 2
    log_handle = None
    try:
        path = os.path.expanduser('~/.local/share/Beer/runner.log')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        log_handle = open(path, 'a', encoding='utf-8', errors='replace')
    except OSError:
        log_handle = None
    try:
        process = subprocess.Popen(
            command, cwd=cwd or None, env=env,
            stdout=log_handle, stderr=subprocess.STDOUT,
        )
    except (OSError, ValueError) as exc:
        _log(f'Failed to start command: {exc}')
        if log_handle is not None:
            log_handle.close()
        return 127
    code = process.wait()
    if log_handle is not None:
        log_handle.close()
    return code


def _run_and_record(app_id, command, cwd=None, env=None):
    global _session
    session = _Session(app_id)
    _session = session
    session.mark_started()
    _log('Launching {}: {}'.format(app_id, ' '.join(command)))
    _install_signal_handlers()
    try:
        code = _spawn(command, cwd=cwd, env=env)
    finally:
        session.record()
        _session = None
    _log('Exited with code {}'.format(code))
    return code


def record_app(app_id, command):
    """Record a launch made through a generated shortcut.

    The command already carries the environment prepared by the ``.desktop``
    file, so it can be spawned as-is.
    """
    config = ConfigManager()
    app = _find_app(config, app_id)
    if app is None:
        # Keep an old shortcut usable even if its application was deleted;
        # there is simply no runtime data to record.
        _log('Application not found, launching without stats: {}'.format(
            app_id
        ))
        return _spawn(command)
    work_dir = os.path.expanduser(app.get('run_directory', '') or '')
    if work_dir and not os.path.isdir(work_dir):
        work_dir = ''
    return _run_and_record(app['app_id'], command, cwd=work_dir)


def run_app(app_id):
    """Reconstruct a saved application's launch command and run it."""
    config = ConfigManager()
    app = _find_app(config, app_id)
    if app is None:
        _log('Application not found: {}'.format(app_id))
        return 2

    more_options = app.get('more_options', {}) or {}
    args_text = more_options.get('startup_args', '') or ''
    try:
        args = shlex.split(args_text) if args_text.strip() else []
    except ValueError:
        args = args_text.split()

    if app.get('native'):
        command_text = app.get('exec_cmd') or app.get('exe_path', '')
        command = shlex.split(command_text) if command_text else []
        if not command:
            _log('No command configured for this application')
            return 2
        return _run_and_record(
            app['app_id'], command,
            cwd=os.path.expanduser(app.get('run_directory', '') or ''),
        )

    runtime_type, prefix, legacy = app_prefix_info(config, app)
    if not runtime_type:
        _log('The application has no Proton/Wine runtime configured')
        return 2

    if prefix_needs_migration(runtime_type, prefix, legacy):
        _log('Migrating legacy prefix {} -> {}'.format(legacy, prefix))
        if not migrate_prefix(legacy, prefix, 'move'):
            _log('Legacy prefix migration failed; using a fresh prefix')

    runtime_path = app.get('proton_path', '')
    runtime = detect_runtime(runtime_path) if runtime_path else None
    if runtime is None:
        _log('Runtime not found: {}'.format(runtime_path))
        return 2

    exe_path = app.get('exe_path', '')
    if not exe_path or not os.path.exists(exe_path):
        _log('Executable not found: {}'.format(exe_path))
        return 2

    wine_options = dict(more_options.get('wine_options', {}) or {})
    compat_data_path = None
    if runtime_type == 'proton':
        compat_data_path = prefix
    elif runtime_type == 'wine' and not wine_options.get('prefix'):
        wine_options['prefix'] = prefix

    env, _wine_prefix = build_runtime_environment(
        runtime,
        wine_options=wine_options,
        env_vars=config.get('environment_variables', {}),
        architecture=app.get('architecture', 'auto'),
        compat_data_path=compat_data_path,
    )
    if compat_data_path:
        env['STEAM_COMPAT_DATA_PATH'] = os.path.expanduser(compat_data_path)
        try:
            os.makedirs(env['STEAM_COMPAT_DATA_PATH'], exist_ok=True)
        except OSError:
            pass
    if runtime_type == 'wine':
        env['WINEPREFIX'] = os.path.expanduser(prefix)

    apply_windows_version(
        runtime, env, wine_options=wine_options,
        output_callback=lambda message, _level='info': _log(message),
    )

    if runtime_type == 'proton':
        proton_script = runtime.get('proton_script') or os.path.join(
            runtime.get('path', ''), 'proton'
        )
        command = [proton_script, 'run', exe_path] + args
    else:
        wine_binary = runtime.get('wine_binary') or wine_binary_for(runtime)
        if not wine_binary:
            _log('Wine binary not found')
            return 2
        command = [wine_binary] + get_wine_arguments(wine_options) + [
            exe_path
        ] + args

    pre_launch = more_options.get('pre_launch_script')
    if pre_launch:
        try:
            subprocess.call(['bash', os.path.expanduser(pre_launch)])
        except OSError as exc:
            _log('Pre-launch script failed: {}'.format(exc))

    work_dir = os.path.expanduser(
        app.get('run_directory', '') or os.path.dirname(exe_path)
    )
    if work_dir and not os.path.isdir(work_dir):
        work_dir = os.path.dirname(exe_path)
    return _run_and_record(app['app_id'], command, cwd=work_dir, env=env)


def cli_main(argv):
    """Entry point for ``--run-app`` and ``--record-app``."""
    if not argv:
        return 2
    mode = argv[0]
    if mode == '--run-app':
        if len(argv) < 2:
            _log('Usage: Beer --run-app <app-id|name>')
            return 2
        return run_app(argv[1])
    if mode == '--record-app':
        # The optional "--" separator may be swallowed by terminal launchers
        # when the desktop entry uses Terminal=true, so it is not required.
        if len(argv) < 3 or not argv[1]:
            _log('Usage: Beer --record-app <app-id> [--] <command...>')
            return 2
        command = argv[2:]
        if command and command[0] == '--':
            command = command[1:]
        if not command:
            _log('Usage: Beer --record-app <app-id> [--] <command...>')
            return 2
        return record_app(argv[1], command)
    _log('Unknown mode: {}'.format(mode))
    return 2
