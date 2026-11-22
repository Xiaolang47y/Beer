# -*- coding: utf-8 -*-
"""
Desktop file generator for Beer

Generates standards compliant ``.desktop`` files for the freedesktop.org
desktop entry specification.
"""

import os
import re
import shlex
import subprocess
import sys

from core.runtime_utils import (
    default_wine_prefix,
    detect_runtime,
    expand_path,
    get_steam_compat_env,
    get_wine_arguments,
    wine_binary_for,
    wine_option_environment,
)

DEFAULT_CATEGORIES = 'Game;'
APPLICATIONS_DIRS = (
    '~/.local/share/applications',
    '~/Applications',
)


def _desktop_value(value):
    """Escape a value used outside the Exec field."""
    value = str(value or '')
    value = value.replace('\\', '\\\\')
    value = value.replace('\n', '\\n').replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value


def _quote_exec_arg(value):
    """Quote one argument for the Exec field of a .desktop file."""
    value = str(value or '')
    # A literal percent sign has to be doubled inside Exec.
    value = value.replace('%', '%%')
    # Characters that must be escaped inside double quotes.
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace('`', '\\`')
    value = value.replace('$', '\\$')
    return f'"{value}"'


def _split_args(args):
    if not args:
        return []
    if isinstance(args, str):
        try:
            return shlex.split(args)
        except ValueError:
            return args.split()
    return [str(arg) for arg in args]


def beer_launch_command():
    """Return the argv needed to start Beer itself.

    Generated shortcuts use this to record the launch time even when the
    graphical interface is closed.
    """
    if getattr(sys, 'frozen', False):
        return [os.environ.get('APPIMAGE') or sys.executable]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [sys.executable, os.path.join(project_root, 'main.py')]


def _sanitize_filename(name):
    name = str(name or 'program').strip()
    name = name.replace('/', '_').replace('\\', '_')
    name = re.sub(r'[^0-9A-Za-z._\-\u4e00-\u9fff ]+', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip('._-') or 'program'
    return name[:120]


def sanitize_filename(name):
    """Public helper used by the desktop entry dialog."""
    return _sanitize_filename(name)


def get_default_icon_path():
    """Return the beer emoji icon PNG path when Qt is available."""
    try:
        from core.app_icon import get_icon_path
        return get_icon_path()
    except Exception:
        return ''


class DesktopGenerator:
    """Generates .desktop files for Linux desktop environments."""

    def __init__(self, icon_path=None):
        self.desktop_dir = self._get_desktop_dir()
        self.default_icon_path = icon_path or get_default_icon_path()

    # ------------------------------------------------------------------
    # Directories
    # ------------------------------------------------------------------
    def _get_desktop_dir(self):
        """Detect desktop directory (supports Chinese locale)."""
        # Honour the user-dirs configuration first.
        user_dirs = os.path.expanduser('~/.config/user-dirs.dirs')
        if os.path.isfile(user_dirs):
            try:
                with open(user_dirs, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('XDG_DESKTOP_DIR='):
                            value = line.split('=', 1)[1].strip().strip('"')
                            value = value.replace('$HOME', os.path.expanduser('~'))
                            if os.path.isdir(value):
                                return value
            except OSError:
                pass

        try:
            result = subprocess.run(
                ['xdg-user-dir', 'DESKTOP'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                if path and os.path.isdir(path):
                    return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        home = os.path.expanduser('~')
        for name in ['Desktop', '桌面']:
            path = os.path.join(home, name)
            if os.path.isdir(path):
                return path

        return os.path.join(home, 'Desktop')

    def _applications_dir(self):
        for path in APPLICATIONS_DIRS:
            path = os.path.expanduser(path)
            if os.path.isdir(path):
                return path
        path = os.path.expanduser(APPLICATIONS_DIRS[0])
        os.makedirs(path, exist_ok=True)
        return path

    def resolve_target_dir(self, target='desktop', desktop_dir=None):
        """Return the directory a desktop entry should be written to."""
        if target == 'custom':
            return expand_path(desktop_dir) or self.desktop_dir
        if target == 'applications':
            return self._applications_dir()
        return self.desktop_dir

    # ------------------------------------------------------------------
    # Command construction
    # ------------------------------------------------------------------
    def _desktop_environment(self, runtime, wine_options, env_vars,
                             compat_data_path=None):
        env = {}

        if runtime and runtime.get('type') == 'proton':
            env.update(get_steam_compat_env(
                runtime.get('path'), compat_data_path
            ))
        elif runtime and runtime.get('type') == 'wine':
            prefix = expand_path((wine_options or {}).get('prefix', '')) or default_wine_prefix()
            env['WINEPREFIX'] = prefix
            env.update(wine_option_environment(wine_options))
        else:
            env.update(wine_option_environment(wine_options))

        if env_vars:
            for key, value in env_vars.items():
                if key:
                    env[str(key)] = str(value)
        return env

    def build_command(self, exe_path, runtime=None, args=None, env_vars=None,
                      wine_options=None, working_dir=None, app_id='',
                      compat_data_path=None):
        """Build the ``Exec`` command string."""
        argv = []
        env = self._desktop_environment(
            runtime, wine_options, env_vars, compat_data_path
        )
        if env:
            argv.append('env')
            argv.extend(f'{key}={value}' for key, value in env.items())

        if runtime and runtime.get('type') == 'proton':
            proton_script = runtime.get('proton_script') or os.path.join(
                runtime.get('path', ''), 'proton'
            )
            argv.extend([proton_script, 'run', exe_path])
            argv.extend(_split_args(args))
        elif runtime and runtime.get('type') == 'wine':
            wine_binary = runtime.get('wine_binary') or wine_binary_for(runtime)
            argv.append(wine_binary)
            argv.extend(get_wine_arguments(wine_options))
            argv.append(exe_path)
            argv.extend(_split_args(args))
        else:
            argv.append(exe_path)
            argv.extend(_split_args(args))

        if app_id:
            # Route the shortcut through Beer's headless recorder so launch
            # time and total runtime are tracked with the UI closed.
            argv = beer_launch_command() + [
                '--record-app', str(app_id), '--'
            ] + argv

        return ' '.join(_quote_exec_arg(part) for part in argv)

    # ------------------------------------------------------------------
    # Validation and preview
    # ------------------------------------------------------------------
    def validate_options(self, name=None, exe_path=None, working_dir=None,
                         runtime_path=None, icon_path=None, terminal=False,
                         target='desktop', desktop_dir=None, filename=None,
                         translator=None):
        """Validate desktop entry options.

        Returns a dict with ``errors`` and ``warnings`` lists.  When a
        translator is supplied, all messages are localized.
        """
        errors = []
        warnings = []

        def text(key, default, **kwargs):
            message = translator(key, default) if translator else default
            try:
                return message.format(**kwargs)
            except (KeyError, IndexError):
                return message

        if not str(name or '').strip():
            errors.append(text(
                'desktop_error_name_required',
                'The desktop entry name is required.'
            ))
        if not str(exe_path or '').strip():
            errors.append(text(
                'desktop_error_exe_required',
                'The executable path is required.'
            ))
        elif not os.path.isfile(expand_path(exe_path)):
            errors.append(text(
                'desktop_error_exe_missing',
                'Executable not found: {path}', path=exe_path
            ))

        if working_dir and not os.path.isdir(expand_path(working_dir)):
            warnings.append(text(
                'desktop_warning_working_dir_missing',
                'Working directory does not exist: {path}', path=working_dir
            ))

        if runtime_path:
            runtime = detect_runtime(runtime_path)
            if runtime is None:
                errors.append(text(
                    'desktop_error_runtime_invalid',
                    'The selected Proton/Wine runtime is not valid.'
                ))

        if icon_path and not os.path.isfile(expand_path(icon_path)):
            warnings.append(text(
                'desktop_warning_icon_missing',
                'The selected icon file does not exist; the beer emoji icon will be used.'
            ))

        if filename:
            cleaned = _sanitize_filename(filename)
            if cleaned + '.desktop' != filename and filename != cleaned:
                warnings.append(text(
                    'desktop_warning_filename_sanitized',
                    'The file name has been sanitised for the desktop entry.'
                ))

        target_dir = self.resolve_target_dir(target, desktop_dir)
        if target == 'custom' and not target_dir:
            errors.append(text(
                'desktop_error_custom_dir_required',
                'A custom output directory is required.'
            ))

        if terminal:
            warnings.append(text(
                'desktop_warning_terminal',
                'Terminal=true will keep a terminal window open while the program runs.'
            ))

        if os.name == 'nt':
            warnings.append(text(
                'desktop_warning_windows',
                'Desktop entries are not supported on Windows.'
            ))

        return {'errors': errors, 'warnings': warnings}

    def build_desktop_content(self, name, exe_path, icon_path=None,
                              working_dir=None, runtime_path=None,
                              env_vars=None, args=None, comment=None,
                              terminal=False, categories=DEFAULT_CATEGORIES,
                              wine_options=None, app_id='',
                              compat_data_path=None):
        """Return the text content of a .desktop file."""
        runtime = detect_runtime(runtime_path) if runtime_path else None

        if not icon_path or not os.path.isfile(expand_path(icon_path)):
            usable_icon = self.default_icon_path
        else:
            usable_icon = expand_path(icon_path)

        command = self.build_command(
            exe_path=expand_path(exe_path),
            runtime=runtime,
            args=args,
            env_vars=env_vars,
            wine_options=wine_options,
            working_dir=working_dir,
            app_id=app_id,
            compat_data_path=compat_data_path,
        )

        categories = (categories or DEFAULT_CATEGORIES).strip() or DEFAULT_CATEGORIES
        if not categories.endswith(';'):
            categories += ';'

        lines = [
            '[Desktop Entry]',
            'Version=1.0',
            'Type=Application',
            f'Name={_desktop_value(name)}',
            f'Comment={_desktop_value(comment or name)}',
            f'Exec={command}',
        ]

        if working_dir:
            lines.append(f'Path={_desktop_value(expand_path(working_dir))}')

        if usable_icon and os.path.isfile(expand_path(usable_icon)):
            lines.append(f'Icon={_desktop_value(expand_path(usable_icon))}')
        else:
            lines.append('Icon=application-x-executable')

        lines.extend([
            f'Terminal={"true" if terminal else "false"}',
            f'Categories={_desktop_value(categories)}',
            'StartupNotify=true',
            'Keywords=Wine;Proton;Windows;',
        ])

        if runtime:
            lines.append(f'X-Beer-Runtime={_desktop_value(runtime.get("name", ""))}')

        return '\n'.join(lines) + '\n'

    def generate_desktop_file(self, name=None, exe_path=None, icon_path=None,
                              working_dir=None, proton_path=None, env_vars=None,
                              args=None, comment=None, terminal=False,
                              categories=DEFAULT_CATEGORIES, desktop_dir=None,
                              filename=None, wine_options=None,
                              runtime_path=None, target='desktop',
                              overwrite=True, architecture=None,
                              translator=None, app_id='',
                              compat_data_path=None):
        """Generate a .desktop file.

        ``proton_path`` is kept as a backwards compatible alias for
        ``runtime_path``.  Returns ``(success, path_or_error)``.
        """
        runtime_path = runtime_path or proton_path

        validation = self.validate_options(
            name=name, exe_path=exe_path, working_dir=working_dir,
            runtime_path=runtime_path, icon_path=icon_path,
            terminal=terminal, target=target, desktop_dir=desktop_dir,
            filename=filename, translator=translator,
        )
        if validation['errors']:
            return False, '; '.join(validation['errors'])

        target_dir = self.resolve_target_dir(target, desktop_dir)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as exc:
            return False, f'Cannot create output directory: {exc}'

        if filename:
            base = _sanitize_filename(os.path.splitext(os.path.basename(filename))[0])
        else:
            base = _sanitize_filename(name)
        desktop_filename = base + '.desktop'
        desktop_path = os.path.join(target_dir, desktop_filename)

        if os.path.exists(desktop_path) and not overwrite:
            return False, f'File already exists: {desktop_path}'

        content = self.build_desktop_content(
            name=name,
            exe_path=exe_path,
            icon_path=icon_path,
            working_dir=working_dir,
            runtime_path=runtime_path,
            env_vars=env_vars,
            args=args,
            comment=comment,
            terminal=terminal,
            categories=categories,
            wine_options=wine_options,
            app_id=app_id,
            compat_data_path=compat_data_path,
        )

        try:
            with open(desktop_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.chmod(desktop_path, 0o755)
        except OSError as exc:
            return False, str(exc)

        # GNOME requires desktop files on the desktop to be marked trusted.
        if target == 'desktop':
            try:
                subprocess.run(
                    ['gio', 'set', desktop_path, 'metadata::trusted', 'true'],
                    capture_output=True, timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass

        if target == 'applications':
            try:
                subprocess.run(
                    ['update-desktop-database', target_dir],
                    capture_output=True, timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                pass

        return True, desktop_path

    # ------------------------------------------------------------------
    # Legacy helpers
    # ------------------------------------------------------------------
    def _get_steam_compat_paths(self, proton_path=None):
        """Backwards compatible helper returning Steam compat variables."""
        return get_steam_compat_env(proton_path) or None

    def delete_desktop_file(self, name, target='desktop', desktop_dir=None):
        """Delete a .desktop file created for *name*."""
        target_dir = self.resolve_target_dir(target, desktop_dir)
        safe_name = _sanitize_filename(name)
        desktop_path = os.path.join(target_dir, safe_name + '.desktop')

        if os.path.exists(desktop_path):
            try:
                os.remove(desktop_path)
                return True
            except OSError:
                return False
        return True
