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
    steam_root = find_steam_root()
    if not steam_root:
        return {}
    data_path = expand_path(compat_data_path) or default_compat_data_path()
    try:
        os.makedirs(data_path, exist_ok=True)
    except OSError:
        return {}
    return {
        'STEAM_COMPAT_CLIENT_INSTALL_PATH': steam_root,
        'STEAM_COMPAT_DATA_PATH': data_path,
        'SteamAppId': '0',
        'SteamGameId': '0',
    }


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
                              architecture=None):
    """Build the environment used to launch a program.

    Returns ``(environment, wine_prefix)``.
    """
    env = os.environ.copy()
    options = wine_options or {}
    prefix = ''

    if runtime and runtime.get('type') == 'proton':
        env.update(get_steam_compat_env(runtime.get('path')))
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
