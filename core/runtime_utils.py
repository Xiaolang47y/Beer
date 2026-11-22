# -*- coding: utf-8 -*-
"""
Shared Proton / Wine runtime detection helpers for Beer.

This module intentionally has no GUI dependencies so it can be used by the
desktop generator, the Winetricks manager and unit tests alike.
"""

import os
import re
import shutil
import subprocess
import uuid

PROTON_SCRIPT_NAMES = ('proton',)
WINE_BINARY_NAMES = ('wine', 'wine64', 'wine-stable', 'wine-staging', 'wine-devel')

_WINE_VERSION_CACHE = {}


def expand_path(path):
    """Expand a leading ``~`` and normalise an empty value to ``''``."""
    if not path:
        return ''
    return os.path.expanduser(str(path))


def _existing_unique(paths):
    """Return existing paths without duplicates (symlink aware)."""
    result = []
    seen = set()
    for path in paths:
        path = expand_path(path)
        if not path or not os.path.exists(path):
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        result.append(path)
    return result


def steam_roots():
    """Return existing Steam installation roots (Linux, Flatpak and macOS)."""
    candidates = [
        '~/.steam/steam',
        '~/.steam/root',
        '~/.local/share/Steam',
        '/usr/share/steam',
        '/usr/local/share/steam',
        '~/.var/app/com.valvesoftware.Steam/.local/share/Steam',
        '~/.var/app/com.valvesoftware.Steam/.steam/steam',
        '~/Library/Application Support/Steam',
    ]
    return _existing_unique(candidates)


def default_proton_search_paths():
    """Default directories that contain Proton installations."""
    paths = [os.path.join(root, 'steamapps', 'common') for root in steam_roots()]
    paths.extend([
        '~/.local/share/Beer/proton',
        '~/.local/share/Steam/steamapps/common',
    ])
    return _existing_unique(paths)


def default_wine_search_paths():
    """Default directories that may contain Wine installations."""
    candidates = [
        '~/.local/share/lutris/runners/wine',
        '~/.local/share/bottles/runners',
        '~/.local/share/wine',
        '~/.local/share/Beer/wine',
        '/opt',
        '/usr/lib/wine',
        '/usr/lib64/wine',
        '/usr/local/lib/wine',
        '/Applications',
        '~/Applications',
        '~/Library/Application Support/Whisky/Libraries/Wine',
        '~/Library/Application Support/net.winehq.wine',
    ]
    # Bottles "runners" are flatpak-only on some distros.
    candidates.append('~/.var/app/com.usebottles.bottles/data/bottles/runners')
    return _existing_unique(candidates)


def find_proton_script(path):
    """Return the Proton launcher script for *path*, or ``None``."""
    path = expand_path(path)
    if not path:
        return None
    if os.path.isfile(path) and os.path.basename(path) in PROTON_SCRIPT_NAMES:
        return path
    if not os.path.isdir(path):
        return None
    for name in ('proton', os.path.join('files', 'bin', 'proton')):
        candidate = os.path.join(path, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _is_executable_file(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def find_wine_binary(path):
    """Return a Wine binary for an installation directory or binary path."""
    path = expand_path(path)
    if not path:
        return None
    base = os.path.basename(path)
    if os.path.isfile(path) and base.startswith('wine') and _is_executable_file(path):
        return path
    if not os.path.isdir(path):
        return None

    candidates = [
        os.path.join(path, 'bin', 'wine'),
        os.path.join(path, 'bin', 'wine64'),
        os.path.join(path, 'wine'),
        os.path.join(path, 'wine64'),
        # macOS .app bundles
        os.path.join(path, 'Contents', 'Resources', 'wine', 'bin', 'wine'),
        os.path.join(path, 'Contents', 'Resources', 'wine', 'bin', 'wine64'),
    ]
    for candidate in candidates:
        if _is_executable_file(candidate):
            return candidate
    return None


def get_wine_version(wine_binary):
    """Return a version string such as ``10.0`` for a Wine binary."""
    if not wine_binary:
        return 'unknown'
    real = os.path.realpath(wine_binary)
    if real in _WINE_VERSION_CACHE:
        return _WINE_VERSION_CACHE[real]

    version = 'unknown'
    try:
        result = subprocess.run(
            [wine_binary, '--version'],
            capture_output=True, text=True, timeout=8, errors='replace'
        )
        output = ((result.stdout or '') + (result.stderr or '')).strip()
        match = re.search(r'wine-([0-9][0-9A-Za-z._\-]*)', output)
        if match:
            version = match.group(1)
        elif output:
            version = output.splitlines()[0].strip()
    except Exception:
        version = 'unknown'

    _WINE_VERSION_CACHE[real] = version
    return version


def parse_version_tuple(version_str):
    """Convert a version string to a tuple of integers for sorting."""
    return tuple(int(part) for part in re.findall(r'\d+', str(version_str)))


def version_from_name(name):
    """Extract a human readable version from a Proton directory name."""
    base = os.path.basename(str(name).strip())
    lowered = base.lower()

    # GE-Proton9-20 / Proton-GE 9-20
    match = re.search(r'(\d+)-(\d+)', base)
    if match:
        return f"{match.group(1)}-{match.group(2)}"

    # Proton 9.0 / Proton-9.0.1 / Proton-CachyOS 9.0
    match = re.search(r'(\d+\.\d+(?:\.\d+)?)', base)
    if match:
        return match.group(1)

    if 'experimental' in lowered:
        return 'Experimental'

    match = re.search(r'(\d+)', base)
    if match:
        return match.group(1)

    return 'unknown'


def _wine_display_name(root, version):
    root = expand_path(root)
    base = os.path.basename(root.rstrip(os.sep))
    if base in ('bin', 'wine', 'wine64') or root in ('/usr/bin', '/usr/local/bin', '/opt/homebrew/bin'):
        return 'Wine (system)'
    if base:
        return base
    return f"Wine {version}"


def detect_runtime(path, source='auto'):
    """Detect a Proton or Wine installation at *path*.

    Returns a dict with ``name``, ``type``, ``version``, ``version_str``,
    ``path``, ``source`` and either ``proton_script`` or ``wine_binary``.
    """
    path = expand_path(path)
    if not path or not os.path.exists(path):
        return None

    # A directory containing a ``proton`` script is a Proton installation.
    proton_script = find_proton_script(path)
    if proton_script:
        root = path if os.path.isdir(path) else os.path.dirname(path)
        version_str = version_from_name(os.path.basename(root))
        return {
            'name': os.path.basename(root) or 'Proton',
            'type': 'proton',
            'version': parse_version_tuple(version_str),
            'version_str': version_str,
            'path': root,
            'proton_script': proton_script,
            'source': source,
            'custom': False,
            'custom_root': '',
        }

    wine_binary = find_wine_binary(path)
    if wine_binary:
        root = path if os.path.isdir(path) else os.path.dirname(path)
        version_str = get_wine_version(wine_binary)
        return {
            'name': _wine_display_name(root, version_str),
            'type': 'wine',
            'version': parse_version_tuple(version_str),
            'version_str': version_str,
            'path': root,
            'wine_binary': wine_binary,
            'source': source,
            'custom': False,
            'custom_root': '',
        }

    return None


def runtime_key(runtime):
    """Stable key used to de-duplicate runtime entries."""
    return runtime.get('type', ''), os.path.realpath(runtime.get('path', ''))


def find_steam_root():
    roots = steam_roots()
    return roots[0] if roots else ''


def default_compat_data_path():
    return os.path.expanduser('~/.local/share/Beer/compatdata/default')


def default_wine_prefix_dir():
    return os.path.expanduser('~/.local/share/Beer/prefixes')


def default_wine_prefix():
    return os.path.join(default_wine_prefix_dir(), 'default')


def get_steam_compat_env(proton_path=None, compat_data_path=None):
    """Build Steam compatibility environment variables for Proton."""
    data_path = expand_path(compat_data_path) or default_compat_data_path()
    try:
        os.makedirs(data_path, exist_ok=True)
    except OSError:
        return {}
    env = {
        'STEAM_COMPAT_DATA_PATH': data_path,
        'SteamAppId': '0',
        'SteamGameId': '0',
    }
    steam_root = find_steam_root()
    if steam_root:
        env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = steam_root
    return env


def default_compat_data_dir():
    """Directory that stores per-application Proton prefixes."""
    return os.path.expanduser('~/.local/share/Beer/compatdata')


def _safe_component(value, fallback='app'):
    safe = re.sub(r'[^0-9A-Za-z._-]+', '-', str(value or '')).strip('-._')
    return (safe or fallback)[:40]


def generate_app_id(app, existing=()):
    """Return a unique, filesystem-safe identifier for an application."""
    current = str((app or {}).get('app_id') or '').strip()
    if current:
        return current
    base = _safe_component((app or {}).get('name'), 'app').lower()
    existing = set(existing or ())
    while True:
        candidate = f'{base}-{uuid.uuid4().hex[:8]}'
        if candidate not in existing:
            return candidate


def app_runtime_type(app):
    """Return ``'proton'``, ``'wine'`` or ``''`` for a saved application."""
    app = app or {}
    if app.get('native'):
        return ''
    runtime_type = str(app.get('runtime_type') or '').lower()
    if runtime_type in ('proton', 'wine'):
        return runtime_type
    path = str(app.get('proton_path') or '')
    if not path:
        return ''
    runtime = detect_runtime(path)
    if runtime:
        return runtime.get('type', '')
    lower = os.path.basename(path).lower()
    if 'proton' in lower:
        return 'proton'
    if 'wine' in lower:
        return 'wine'
    return ''


def app_prefix_info(config, app):
    """Return ``(runtime_type, prefix_path, legacy_path)`` for an app.

    Proton uses ``STEAM_COMPAT_DATA_PATH`` while Wine uses ``WINEPREFIX``.
    ``legacy_path`` is the old shared prefix used by earlier Beer versions;
    it is empty when the application already has an explicit custom prefix.
    """
    app = app or {}
    runtime_type = app_runtime_type(app)
    if runtime_type == 'proton':
        app_id = app.get('app_id') or _safe_component(app.get('name'))
        path = expand_path(app.get('compat_data_path', '')) or os.path.join(
            default_compat_data_dir(), app_id
        )
        return runtime_type, path, default_compat_data_path()
    if runtime_type == 'wine':
        options = ((app.get('more_options') or {}).get('wine_options') or {})
        explicit = expand_path(options.get('prefix', ''))
        if explicit:
            return runtime_type, explicit, ''
        app_id = app.get('app_id') or _safe_component(app.get('name'))
        base = ''
        if config is not None:
            try:
                base = config.get_wine_prefix_dir()
            except Exception:
                base = ''
        path = expand_path(app.get('wine_prefix', '')) or os.path.join(
            base or default_wine_prefix_dir(), app_id
        )
        return runtime_type, path, default_wine_prefix()
    return '', '', ''


def ensure_app_prefix_fields(config, app):
    """Fill ``app_id`` and default prefix fields in place.

    Returns True when the application dict was modified.
    """
    app = app or {}
    changed = False
    if not app.get('app_id'):
        app['app_id'] = generate_app_id(app)
        changed = True
    runtime_type = app_runtime_type(app)
    if runtime_type == 'proton' and not app.get('compat_data_path'):
        app['compat_data_path'] = os.path.join(
            default_compat_data_dir(), app['app_id']
        )
        changed = True
    if runtime_type == 'wine':
        options = ((app.get('more_options') or {}).get('wine_options') or {})
        if not expand_path(options.get('prefix', '')) and not app.get('wine_prefix'):
            base = ''
            if config is not None:
                try:
                    base = config.get_wine_prefix_dir()
                except Exception:
                    base = ''
            app['wine_prefix'] = os.path.join(
                base or default_wine_prefix_dir(), app['app_id']
            )
            changed = True
    return changed


def prefix_has_data(prefix_path, runtime_type):
    """Return True when a prefix directory already contains a Wine prefix."""
    if not prefix_path or not os.path.isdir(prefix_path):
        return False
    if runtime_type == 'proton':
        return os.path.isdir(os.path.join(prefix_path, 'pfx'))
    if runtime_type == 'wine':
        return os.path.isdir(os.path.join(prefix_path, 'drive_c'))
    return bool(os.listdir(prefix_path))


def prefix_needs_migration(runtime_type, prefix_path, legacy_path):
    """Return True when legacy data exists and the new prefix is still empty."""
    if not runtime_type or not legacy_path or not prefix_path:
        return False
    if os.path.realpath(prefix_path) == os.path.realpath(legacy_path):
        return False
    return (
        not prefix_has_data(prefix_path, runtime_type)
        and prefix_has_data(legacy_path, runtime_type)
    )


def migrate_prefix(legacy_path, target_path, mode='move'):
    """Move or copy an old shared prefix to a per-application location."""
    if not legacy_path or not target_path:
        return False
    if os.path.realpath(legacy_path) == os.path.realpath(target_path):
        return False
    if not os.path.isdir(legacy_path):
        return False
    if os.path.isdir(target_path) and os.listdir(target_path):
        return False
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if mode == 'copy':
            shutil.copytree(legacy_path, target_path, dirs_exist_ok=True)
        else:
            if os.path.isdir(target_path):
                os.rmdir(target_path)
            shutil.move(legacy_path, target_path)
        return True
    except (OSError, shutil.Error):
        return False


def wine_binary_for(runtime):
    """Return the Wine binary used internally by a Proton/Wine runtime."""
    if not runtime:
        return None
    if runtime.get('type') == 'wine':
        return runtime.get('wine_binary') or find_wine_binary(runtime.get('path'))
    root = runtime.get('path', '')
    for candidate in (
        os.path.join(root, 'dist', 'bin', 'wine'),
        os.path.join(root, 'files', 'bin', 'wine'),
        os.path.join(root, 'dist', 'bin', 'wine64'),
    ):
        if _is_executable_file(candidate):
            return candidate
    return None


def wine_option_environment(wine_options):
    """Translate user facing Wine options into environment variables."""
    options = wine_options or {}
    env = {}

    dll_overrides = str(options.get('dll_overrides', '') or '').strip()
    if dll_overrides:
        env['WINEDLLOVERRIDES'] = dll_overrides

    debug = str(options.get('debug', '') or '').strip()
    debug_map = {
        'none': '-all',
        'err': 'err',
        'warn': 'warn+err',
        'fixme': 'fixme+err',
        'all': '',
    }
    if debug in debug_map and debug_map[debug]:
        env['WINEDEBUG'] = debug_map[debug]

    if options.get('esync'):
        env['WINEESYNC'] = '1'
    if options.get('fsync'):
        env['WINEFSYNC'] = '1'
    if options.get('use_wined3d'):
        env['PROTON_USE_WINED3D'] = '1'

    return env


def _apply_wine_option_env(env, wine_options):
    env.update(wine_option_environment(wine_options))


def build_runtime_environment(runtime, wine_options=None, env_vars=None,
                              architecture=None, compat_data_path=None):
    """Build the environment used to launch a program.

    Returns ``(environment, wine_prefix)``.
    """
    env = os.environ.copy()
    options = wine_options or {}
    prefix = ''

    if runtime and runtime.get('type') == 'proton':
        env.update(get_steam_compat_env(
            runtime.get('path'), compat_data_path
        ))
    elif runtime and runtime.get('type') == 'wine':
        prefix = expand_path(options.get('prefix', '')) or default_wine_prefix()
        newly_created = not os.path.isdir(prefix)
        try:
            os.makedirs(prefix, exist_ok=True)
        except OSError:
            pass
        env['WINEPREFIX'] = prefix
        if newly_created and architecture == '32':
            env['WINEARCH'] = 'win32'
        elif newly_created and architecture == '64':
            env['WINEARCH'] = 'win64'

    _apply_wine_option_env(env, options)

    if env_vars:
        for key, value in env_vars.items():
            if key:
                env[str(key)] = str(value)

    return env, prefix


def get_wine_arguments(wine_options):
    """Return extra command line arguments for the Wine binary."""
    import shlex
    extra = str((wine_options or {}).get('extra_args', '') or '').strip()
    if not extra:
        return []
    try:
        return shlex.split(extra)
    except ValueError:
        return extra.split()


def apply_windows_version(runtime, env, wine_options=None, output_callback=None):
    """Apply the requested Windows version to a Wine prefix.

    Uses ``wine reg add`` so it works with both Wine and Proton runtimes.
    """
    version = str((wine_options or {}).get('windows_version', '') or '').strip()
    if not version or version == 'default':
        return True

    binary = wine_binary_for(runtime)
    if not binary:
        if output_callback:
            output_callback('Wine binary not found; cannot apply Windows version', 'warning')
        return False

    region = r'HKCU\Software\Wine'
    cmd = [binary, 'reg', 'add', region, '/v', 'Version', '/d', version, '/f']
    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=30, errors='replace'
        )
        output = ((result.stdout or '') + (result.stderr or '')).strip()
        if output and output_callback:
            output_callback(output, 'proton')
        if result.returncode != 0:
            if output_callback:
                output_callback(
                    f'Failed to set Windows version to {version} (code {result.returncode})',
                    'warning'
                )
            return False
        if output_callback:
            output_callback(f'Windows version set to {version}', 'info')
        return True
    except Exception as exc:
        if output_callback:
            output_callback(f'Failed to set Windows version: {exc}', 'warning')
        return False


def is_steam_installed():
    """Return True when a Steam installation can be found."""
    return bool(steam_roots()) or bool(shutil.which('steam'))
