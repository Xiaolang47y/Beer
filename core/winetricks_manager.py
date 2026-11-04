# -*- coding: utf-8 -*-
"""
Winetricks integration for Beer.

The manager itself has no GUI dependencies; the dialog runs the returned
command with :class:`QProcess`.
"""

import os
import re
import shutil
import subprocess
import urllib.request

from core.runtime_utils import (
    build_runtime_environment,
    expand_path,
    find_steam_root,
    wine_binary_for,
)

WINETRICKS_DOWNLOAD_URL = (
    'https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks'
)


def _item(verb, name_en, name_zh, category_en, category_zh, desc_en, desc_zh,
          network=False, large=False):
    return {
        'verb': verb,
        'name': {'en': name_en, 'zh': name_zh},
        'category': {'en': category_en, 'zh': category_zh},
        'description': {'en': desc_en, 'zh': desc_zh},
        'network': network,
        'large': large,
    }


# A curated list of commonly used Winetricks verbs.  Descriptions are kept
# bilingual so the table follows the application language.
WINETRICKS_ITEMS = [
    _item('corefonts', 'Core Fonts', '核心字体', 'Fonts', '字体',
          'Install Microsoft core fonts (Arial, Times New Roman, Courier New, etc.).',
          '安装微软核心字体（Arial、Times New Roman、Courier New 等）。', True),
    _item('fontsmooth=rgb', 'Font Smoothing', '字体平滑', 'Fonts', '字体',
          'Enable RGB font smoothing for clearer text.',
          '启用 RGB 字体平滑，让文字更清晰。'),
    _item('vcrun6', 'Visual C++ 6.0', 'Visual C++ 6.0 运行库', 'Runtime', '运行库',
          'Visual C++ 6.0 runtime used by many older games.',
          '许多老游戏需要的 Visual C++ 6.0 运行库。', True),
    _item('vcrun2005', 'Visual C++ 2005', 'Visual C++ 2005 运行库', 'Runtime', '运行库',
          'Visual C++ 2005 runtime (msvcp80 / msvcr80).',
          'Visual C++ 2005 运行库（msvcp80 / msvcr80）。', True),
    _item('vcrun2008', 'Visual C++ 2008', 'Visual C++ 2008 运行库', 'Runtime', '运行库',
          'Visual C++ 2008 runtime (msvcp90 / msvcr90).',
          'Visual C++ 2008 运行库（msvcp90 / msvcr90）。', True),
    _item('vcrun2010', 'Visual C++ 2010', 'Visual C++ 2010 运行库', 'Runtime', '运行库',
          'Visual C++ 2010 runtime (msvcp100 / msvcr100).',
          'Visual C++ 2010 运行库（msvcp100 / msvcr100）。', True),
    _item('vcrun2012', 'Visual C++ 2012', 'Visual C++ 2012 运行库', 'Runtime', '运行库',
          'Visual C++ 2012 runtime (msvcp110 / msvcr110).',
          'Visual C++ 2012 运行库（msvcp110 / msvcr110）。', True),
    _item('vcrun2013', 'Visual C++ 2013', 'Visual C++ 2013 运行库', 'Runtime', '运行库',
          'Visual C++ 2013 runtime (msvcp120 / msvcr120).',
          'Visual C++ 2013 运行库（msvcp120 / msvcr120）。', True),
    _item('vcrun2015', 'Visual C++ 2015', 'Visual C++ 2015 运行库', 'Runtime', '运行库',
          'Visual C++ 2015 runtime (Universal CRT).',
          'Visual C++ 2015 运行库（Universal CRT）。', True),
    _item('vcrun2019', 'Visual C++ 2019', 'Visual C++ 2019 运行库', 'Runtime', '运行库',
          'Visual C++ 2019 runtime (VC 14.x).',
          'Visual C++ 2019 运行库（VC 14.x）。', True),
    _item('vcrun2022', 'Visual C++ 2022', 'Visual C++ 2022 运行库', 'Runtime', '运行库',
          'Visual C++ 2022 runtime (VC 14.3x).',
          'Visual C++ 2022 运行库（VC 14.3x）。', True),
    _item('dotnet35', '.NET Framework 3.5', '.NET Framework 3.5', 'Framework', '框架',
          'Microsoft .NET Framework 3.5 (includes 2.0 and 3.0).',
          '微软 .NET Framework 3.5（包含 2.0 与 3.0）。', True, True),
    _item('dotnet40', '.NET Framework 4.0', '.NET Framework 4.0', 'Framework', '框架',
          'Microsoft .NET Framework 4.0.',
          '微软 .NET Framework 4.0。', True, True),
    _item('dotnet452', '.NET Framework 4.5.2', '.NET Framework 4.5.2', 'Framework', '框架',
          'Microsoft .NET Framework 4.5.2.',
          '微软 .NET Framework 4.5.2。', True, True),
    _item('dotnet462', '.NET Framework 4.6.2', '.NET Framework 4.6.2', 'Framework', '框架',
          'Microsoft .NET Framework 4.6.2.',
          '微软 .NET Framework 4.6.2。', True, True),
    _item('dotnet472', '.NET Framework 4.7.2', '.NET Framework 4.7.2', 'Framework', '框架',
          'Microsoft .NET Framework 4.7.2.',
          '微软 .NET Framework 4.7.2。', True, True),
    _item('dotnet48', '.NET Framework 4.8', '.NET Framework 4.8', 'Framework', '框架',
          'Microsoft .NET Framework 4.8.',
          '微软 .NET Framework 4.8。', True, True),
    _item('d3dx9', 'DirectX 9 (d3dx9)', 'DirectX 9（d3dx9）', 'Graphics', '图形',
          'DirectX 9 helper libraries used by many DirectX 9 games.',
          '许多 DirectX 9 游戏需要的辅助库。', True),
    _item('d3dx11_43', 'DirectX 11 (d3dx11)', 'DirectX 11（d3dx11）', 'Graphics', '图形',
          'DirectX 11 D3DX helper libraries from the June 2010 SDK.',
          'DirectX 11 D3DX 辅助库（2010 年 6 月 SDK）。', True),
    _item('d3dcompiler_43', 'D3D Compiler 43', 'D3D 编译器 43', 'Graphics', '图形',
          'Direct3D shader compiler version 43.',
          'Direct3D 着色器编译器 43 版。', True),
    _item('d3dcompiler_47', 'D3D Compiler 47', 'D3D 编译器 47', 'Graphics', '图形',
          'Direct3D shader compiler version 47.',
          'Direct3D 着色器编译器 47 版。', True),
    _item('dxvk', 'DXVK', 'DXVK', 'Graphics', '图形',
          'Direct3D 9/10/11 to Vulkan translation layer.',
          '将 Direct3D 9/10/11 转换为 Vulkan 的转译层。', True),
    _item('vkd3d', 'VKD3D', 'VKD3D', 'Graphics', '图形',
          'Direct3D 12 to Vulkan translation layer.',
          '将 Direct3D 12 转换为 Vulkan 的转译层。', True, True),
    _item('xact', 'XACT Audio', 'XACT 音频', 'Audio', '音频',
          'Microsoft XACT audio engine used by many games.',
          '许多游戏使用的微软 XACT 音频引擎。', True),
    _item('xinput', 'XInput', 'XInput 手柄支持', 'Input', '输入',
          'XInput controller support for gamepads.',
          '为游戏手柄提供 XInput 支持。', True),
    _item('faudio', 'FAudio', 'FAudio', 'Audio', '音频',
          'FAudio / XAudio2 implementation for game audio.',
          '用于游戏音频的 FAudio / XAudio2 实现。', True),
    _item('openal', 'OpenAL', 'OpenAL', 'Audio', '音频',
          'OpenAL audio library.',
          'OpenAL 音频库。', True),
    _item('physx', 'NVIDIA PhysX', 'NVIDIA PhysX', 'Physics', '物理',
          'NVIDIA PhysX runtime used by some games.',
          '部分游戏使用的 NVIDIA PhysX 运行库。', True, True),
    _item('quartz', 'Quartz', 'Quartz 视频', 'Media', '媒体',
          'Quartz / DirectShow video playback support.',
          'Quartz / DirectShow 视频播放支持。', True),
    _item('wmp10', 'Windows Media Player 10', 'Windows Media Player 10', 'Media', '媒体',
          'Windows Media Player 10 codecs and player.',
          'Windows Media Player 10 解码器与播放器。', True),
    _item('wmp11', 'Windows Media Player 11', 'Windows Media Player 11', 'Media', '媒体',
          'Windows Media Player 11 codecs and player.',
          'Windows Media Player 11 解码器与播放器。', True),
    _item('msxml3', 'MSXML 3', 'MSXML 3', 'XML', 'XML',
          'Microsoft XML parser version 3.',
          '微软 XML 解析器第 3 版。', True),
    _item('msxml4', 'MSXML 4', 'MSXML 4', 'XML', 'XML',
          'Microsoft XML parser version 4.',
          '微软 XML 解析器第 4 版。', True),
    _item('msxml6', 'MSXML 6', 'MSXML 6', 'XML', 'XML',
          'Microsoft XML parser version 6.',
          '微软 XML 解析器第 6 版。', True),
    _item('gdiplus', 'GDI+', 'GDI+', 'System', '系统',
          'Microsoft GDI+ graphics library.',
          '微软 GDI+ 图形库。', True),
    _item('riched20', 'RichEdit 2.0', 'RichEdit 2.0', 'System', '系统',
          'RichEdit 2.0 text control.',
          'RichEdit 2.0 文本控件。', True),
    _item('riched30', 'RichEdit 3.0', 'RichEdit 3.0', 'System', '系统',
          'RichEdit 3.0 text control.',
          'RichEdit 3.0 文本控件。', True),
    _item('ie8', 'Internet Explorer 8', 'Internet Explorer 8', 'Browser', '浏览器',
          'Internet Explorer 8 (useful for old launchers).',
          'Internet Explorer 8（适用于旧启动器）。', True, True),
    _item('win7', 'Windows 7 mode', 'Windows 7 模式', 'Version', '系统版本',
          'Report Windows 7 to applications.',
          '向应用程序报告 Windows 7 版本。'),
    _item('win8', 'Windows 8 mode', 'Windows 8 模式', 'Version', '系统版本',
          'Report Windows 8 to applications.',
          '向应用程序报告 Windows 8 版本。'),
    _item('win10', 'Windows 10 mode', 'Windows 10 模式', 'Version', '系统版本',
          'Report Windows 10 to applications.',
          '向应用程序报告 Windows 10 版本。'),
    _item('win11', 'Windows 11 mode', 'Windows 11 模式', 'Version', '系统版本',
          'Report Windows 11 to applications.',
          '向应用程序报告 Windows 11 版本。'),
]

ITEM_BY_VERB = {item['verb']: item for item in WINETRICKS_ITEMS}

# Category headings used by ``winetricks list-all``.
WINETRICKS_CATEGORIES = {
    'apps': ('Applications', '应用程序'),
    'benchmarks': ('Benchmarks', '基准测试'),
    'dlls': ('DLLs', 'DLL 组件'),
    'fonts': ('Fonts', '字体'),
    'prefix': ('Prefix', 'Wine 前缀'),
    'settings': ('Settings', '设置'),
}


def parse_list_all(output):
    """Parse ``winetricks list-all`` output into item dictionaries.

    Winetricks prints category headings followed by lines in the form
    ``verb  description``.  Descriptions are preserved so components that are
    not in the built-in list still have useful text in the table.
    """
    items = []
    category_en, category_zh = 'Other', '其他'
    for raw_line in (output or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('======') or line.startswith('====='):
            heading = line.strip('= ').strip().lower()
            category_en, category_zh = WINETRICKS_CATEGORIES.get(
                heading, (heading.title() or 'Other', heading or '其他')
            )
            continue
        if line.startswith('#') or line.startswith('---'):
            continue

        parts = line.split(None, 1)
        verb = parts[0]
        if not verb or verb.startswith('--') or verb.startswith('====='):
            continue
        description = parts[1].strip() if len(parts) > 1 else ''
        description = re.sub(
            r'\s*\[(?:可下载|downloadable|download)\]', '', description,
            flags=re.IGNORECASE
        ).strip()
        if not description:
            description = f'{verb} (Winetricks component)'

        items.append({
            'verb': verb,
            'name': {'en': verb, 'zh': verb},
            'category': {'en': category_en, 'zh': category_zh},
            'description': {
                'en': description,
                'zh': description,
            },
            'network': True,
            'large': False,
            'discovered': True,
        })
    return items


class WinetricksManager:
    """Locate, download and run Winetricks."""

    def __init__(self, config=None):
        self.config = config
        self._winetricks_path = None

    # ------------------------------------------------------------------
    # Locating / downloading
    # ------------------------------------------------------------------
    def search_paths(self):
        paths = []
        configured = ''
        if self.config is not None:
            try:
                configured = self.config.get('winetricks_path', '') or ''
            except Exception:
                configured = ''
        if configured:
            paths.append(expand_path(configured))

        user_bin = os.path.expanduser('~/.local/share/Beer/bin/winetricks')
        config_bin = os.path.expanduser('~/.config/Beer/bin/winetricks')
        paths.extend([user_bin, config_bin])

        found = shutil.which('winetricks')
        if found:
            paths.append(found)
        return paths

    def find_winetricks(self):
        """Return a usable Winetricks executable path, or ``''``."""
        if self._winetricks_path and os.path.isfile(self._winetricks_path):
            return self._winetricks_path
        for path in self.search_paths():
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                self._winetricks_path = path
                return path
        return ''

    def download_winetricks(self, progress_callback=None):
        """Download the official Winetricks script.

        Returns ``(path, error)``.
        """
        target_dir = os.path.expanduser('~/.local/share/Beer/bin')
        target = os.path.join(target_dir, 'winetricks')
        try:
            os.makedirs(target_dir, exist_ok=True)
            if progress_callback:
                progress_callback('Downloading Winetricks...', 'info')
            with urllib.request.urlopen(WINETRICKS_DOWNLOAD_URL, timeout=60) as response:
                data = response.read()
            with open(target, 'wb') as f:
                f.write(data)
            os.chmod(target, 0o755)
            self._winetricks_path = target
            if self.config is not None:
                try:
                    self.config.set('winetricks_path', target)
                except Exception:
                    pass
            if progress_callback:
                progress_callback(f'Winetricks downloaded to {target}', 'success')
            return target, ''
        except Exception as exc:
            message = f'Failed to download Winetricks: {exc}'
            if progress_callback:
                progress_callback(message, 'error')
            return '', message

    # ------------------------------------------------------------------
    # Environment / command
    # ------------------------------------------------------------------
    def build_environment(self, runtime, prefix=None, wine_options=None, env_vars=None):
        """Build environment variables for Winetricks."""
        wine_options = dict(wine_options or {})
        if prefix:
            wine_options['prefix'] = prefix
        env, actual_prefix = build_runtime_environment(
            runtime, wine_options=wine_options, env_vars=env_vars
        )

        if runtime and runtime.get('type') == 'proton':
            binary = wine_binary_for(runtime)
            if binary:
                env['WINE'] = binary
                bin_dir = os.path.dirname(binary)
                env['PATH'] = bin_dir + os.pathsep + env.get('PATH', '')
                if prefix:
                    # Use the prefix selected in the dialog for the Proton
                    # Wine binary as well.
                    env['WINEPREFIX'] = expand_path(prefix)
                    env['STEAM_COMPAT_DATA_PATH'] = expand_path(prefix)
                else:
                    # Proton's Wine expects the pfx directory to live inside
                    # STEAM_COMPAT_DATA_PATH.
                    data_path = env.get('STEAM_COMPAT_DATA_PATH', '')
                    if data_path:
                        env.setdefault('WINEPREFIX', os.path.join(data_path, 'pfx'))
            env.setdefault(
                'STEAM_COMPAT_CLIENT_INSTALL_PATH',
                find_steam_root()
            )

        if env.get('WINEPREFIX'):
            try:
                os.makedirs(env['WINEPREFIX'], exist_ok=True)
            except OSError:
                pass

        return env, actual_prefix

    def build_command(self, runtime, verbs, prefix=None, wine_options=None):
        """Return ``(argv, environment)`` for a Winetricks run."""
        winetricks = self.find_winetricks()
        if not winetricks:
            return None, None
        env, _prefix = self.build_environment(
            runtime, prefix=prefix, wine_options=wine_options
        )
        argv = [winetricks, '-q'] + list(verbs)
        return argv, env

    def list_installed_verbs(self):
        """Return the Winetricks verbs installed in the current prefix."""
        winetricks = self.find_winetricks()
        if not winetricks:
            return []
        try:
            result = subprocess.run(
                [winetricks, 'list-installed'],
                capture_output=True, text=True, timeout=60, errors='replace'
            )
            return [
                line.strip().split(' ')[0]
                for line in result.stdout.splitlines()
                if line.strip()
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Discovered components cache
    # ------------------------------------------------------------------
    def cached_items(self):
        """Return previously discovered Winetricks components from config."""
        if self.config is None:
            return []
        try:
            cached = self.config.get('winetricks_verbs_cache', []) or []
        except Exception:
            return []
        if not isinstance(cached, list):
            return []
        items = []
        for item in cached:
            if not isinstance(item, dict):
                continue
            verb = str(item.get('verb', '') or '').strip()
            if not verb:
                continue
            description = item.get('description', '') or {}
            if isinstance(description, str):
                description = {'en': description, 'zh': description}
            category = item.get('category', '') or {}
            if isinstance(category, str):
                category = {'en': category, 'zh': category}
            items.append({
                'verb': verb,
                'name': {'en': verb, 'zh': verb},
                'category': {
                    'en': category.get('en', 'Other'),
                    'zh': category.get('zh', '其他'),
                },
                'description': {
                    'en': description.get('en', ''),
                    'zh': description.get('zh', '') or description.get('en', ''),
                },
                'network': True,
                'large': bool(item.get('large', False)),
                'discovered': True,
            })
        return items

    def save_cached_items(self, items):
        """Persist discovered components so they survive a restart."""
        if self.config is None:
            return False
        try:
            self.config.set('winetricks_verbs_cache', list(items or []))
            return True
        except Exception:
            return False

    def refresh_discovered_items(self):
        """Run ``winetricks list-all`` and persist the parsed components."""
        winetricks = self.find_winetricks()
        if not winetricks:
            return self.cached_items()
        try:
            result = subprocess.run(
                [winetricks, 'list-all'],
                capture_output=True, text=True, timeout=120, errors='replace'
            )
            if result.returncode != 0 and not result.stdout.strip():
                return self.cached_items()
            items = parse_list_all(result.stdout)
        except Exception:
            return self.cached_items()

        # Curated entries already have better bilingual descriptions.
        discovered = [
            item for item in items if item['verb'] not in ITEM_BY_VERB
        ]
        self.save_cached_items(discovered)
        return discovered

    def list_all_items(self):
        """Return items from ``winetricks list-all`` with descriptions."""
        return self.refresh_discovered_items()

    def list_all_verbs(self):
        """Return all verbs known to Winetricks (if it is installed)."""
        return [item['verb'] for item in self.list_all_items()]


# ----------------------------------------------------------------------
# Helpers used by the UI
# ----------------------------------------------------------------------
def item_text(item, field, language='en'):
    """Return a bilingual field from a Winetricks item."""
    value = item.get(field, '')
    if isinstance(value, dict):
        return value.get(language) or value.get('en') or ''
    return str(value or '')


def get_items(language='en', include_unknown=False, manager=None):
    """Return the curated item list, optionally merged with cached verbs."""
    items = list(WINETRICKS_ITEMS)
    if include_unknown and manager is not None:
        known = {item['verb'] for item in items}
        for item in manager.cached_items():
            if item['verb'] in known:
                continue
            items.append(item)
    return items


def prefix_for_name(config, name):
    """Return a safe default Wine prefix for an application name."""
    import re
    safe = re.sub(r'[^0-9A-Za-z._\-\u4e00-\u9fff]+', '_', str(name or '').strip())
    safe = safe.strip('._-') or 'default'
    base = ''
    if config is not None:
        try:
            base = config.get_wine_prefix_dir()
        except Exception:
            base = ''
    base = base or os.path.expanduser('~/.local/share/Beer/prefixes')
    return os.path.join(base, safe)
