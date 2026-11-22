# -*- coding: utf-8 -*-
"""Import existing freedesktop ``.desktop`` files into Beer.

The importer understands native Linux entries as well as entries that launch
Windows programs through Proton or Wine.  It never executes anything, it only
reads the desktop entry and converts it into the dictionary format used by
``apps.json``.
"""

import os
import re
import shlex
import shutil

FIELD_CODE_RE = re.compile(r'(?<!%)%[fFuUdDnNickvm]')


def _read_desktop_entry(path):
    """Return the ``[Desktop Entry]`` keys of a desktop file."""
    entries = {}
    group = ''
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                group = line[1:-1].strip()
                continue
            if group != 'Desktop Entry' or '=' not in line:
                continue
            key, value = line.split('=', 1)
            entries[key.strip()] = value.strip()
    return entries


def _localized(entries, key, languages=('zh_CN', 'zh', 'zh_Hans', 'en')):
    """Return a localized value for *key*, falling back to the base key."""
    for language in languages:
        value = entries.get(f'{key}[{language}]')
        if value:
            return value
    return entries.get(key, '')


def _clean_exec(value):
    """Remove desktop field codes from an Exec value."""
    return FIELD_CODE_RE.sub('', value or '').replace('%%', '%').strip()


def _strip_env(argv):
    """Skip a leading ``env`` command with its ``KEY=VALUE`` assignments."""
    if not argv:
        return argv
    if os.path.basename(argv[0]) != 'env':
        return argv
    index = 1
    while index < len(argv) and '=' in argv[index]:
        index += 1
    return argv[index:]


def resolve_icon_path(icon_name):
    """Resolve a themed icon name to a file path when possible."""
    if not icon_name:
        return ''
    icon_name = icon_name.strip()
    if os.path.isabs(icon_name) and os.path.isfile(icon_name):
        return icon_name

    base = os.path.splitext(os.path.basename(icon_name))[0]
    home = os.path.expanduser('~')
    roots = [
        os.path.join(home, '.local', 'share', 'icons'),
        os.path.join(home, '.local', 'share', 'flatpak', 'exports', 'share', 'icons'),
        '/usr/share/icons',
        '/usr/local/share/icons',
        '/var/lib/flatpak/exports/share/icons',
        '/var/lib/snapd/desktop/icons',
    ]
    sizes = ('256x256', '128x128', '96x96', '64x64', '48x48', 'scalable')
    for root in roots:
        for size in sizes:
            for extension in ('.png', '.svg', '.xpm'):
                candidate = os.path.join(
                    root, 'hicolor', size, 'apps', base + extension
                )
                if os.path.isfile(candidate):
                    return candidate

    for directory in (
        '/usr/share/pixmaps',
        os.path.join(home, '.local', 'share', 'pixmaps'),
    ):
        for extension in ('.png', '.svg', '.xpm'):
            candidate = os.path.join(directory, base + extension)
            if os.path.isfile(candidate):
                return candidate

    found = shutil.which(icon_name)
    return found or ''


def _first_exe_argument(argv):
    """Return the first argument that looks like a Windows executable."""
    for argument in argv:
        if argument.lower().endswith('.exe'):
            return argument
    for argument in reversed(argv):
        if not argument.startswith('-'):
            return argument
    return ''


def parse_desktop_file(path):
    """Parse *path* and return an application dictionary.

    Raises :class:`ValueError` when the file is not a usable desktop entry.
    """
    entries = _read_desktop_entry(path)
    if not entries:
        raise ValueError('The desktop file does not contain a [Desktop Entry] section.')

    name = _localized(entries, 'Name') or os.path.splitext(os.path.basename(path))[0]
    comment = _localized(entries, 'Comment')
    icon_name = _localized(entries, 'Icon')
    exec_value = _clean_exec(_localized(entries, 'Exec'))
    if not exec_value:
        raise ValueError('The desktop file has no Exec line.')

    try:
        argv = _strip_env(shlex.split(exec_value))
    except ValueError:
        argv = exec_value.split()
    if not argv:
        raise ValueError('The desktop file has an empty Exec line.')

    working_dir = _localized(entries, 'Path') or ''
    if working_dir and not os.path.isdir(working_dir):
        working_dir = ''

    app = {
        'name': name,
        'description': comment,
        'desktop_file': os.path.abspath(path),
        'icon_name': icon_name,
        'icon_path': resolve_icon_path(icon_name),
        'working_directory': working_dir,
        'run_directory': working_dir,
        'architecture': 'auto',
        'more_options': {},
        'shelves': [],
        'categories': [
            item.strip() for item in entries.get('Categories', '').split(';')
            if item.strip()
        ],
        'native': True,
        'exec_cmd': ' '.join(shlex.quote(part) for part in argv),
        'exe_path': argv[0],
        'runtime_type': '',
        'proton_path': '',
    }

    binary = os.path.basename(argv[0]).lower()
    lower_args = [part.lower() for part in argv]

    # Proton entries: ``.../proton run game.exe``.
    if 'proton' in binary and 'run' in lower_args:
        run_index = lower_args.index('run')
        if run_index + 1 < len(argv):
            exe_path = argv[run_index + 1]
            runtime_root = os.path.dirname(argv[0])
            app.update({
                'native': False,
                'exe_path': exe_path,
                'runtime_type': 'proton',
                'proton_path': runtime_root,
                'exec_cmd': '',
            })

    # Wine entries: a wine binary followed by the Windows executable.
    elif 'wine' in binary:
        exe_path = _first_exe_argument(argv[1:])
        if exe_path:
            app.update({
                'native': False,
                'exe_path': exe_path,
                'runtime_type': 'wine',
                'proton_path': argv[0],
                'exec_cmd': '',
            })

    if app['native']:
        app['exe_path'] = argv[0]

    if not app['run_directory'] and app.get('exe_path'):
        app['run_directory'] = os.path.dirname(app['exe_path'])

    return app
