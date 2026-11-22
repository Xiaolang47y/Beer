# -*- coding: utf-8 -*-
"""
Configuration manager for Beer
"""

import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import uuid

from core.runtime_utils import (
    default_proton_search_paths,
    ensure_app_prefix_fields,
    expand_path,
)


class ConfigManager:
    """Manages application configuration"""

    DEFAULT_CONFIG = {
        'language': 'system',
        'theme': 'system',
        'default_page': 'main',
        'proton_search_paths': default_proton_search_paths(),
        'wine_search_paths': [],
        'custom_proton_paths': [],
        'environment_variables': {},
        'show_log_on_start': False,
        'log_auto_scroll': True,
        'wine_prefix_dir': os.path.expanduser('~/.local/share/Beer/prefixes'),
        'winetricks_path': '',
        'winetricks_verbs_cache': [],
        'sort_mode': 'name',
        'shelves': [
            {'id': 'preset:recent', 'preset': 'recent'},
            {'id': 'preset:all', 'preset': 'all'},
        ],
    }

    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.apps_file = os.path.join(self.config_dir, 'apps.json')
        self.config = self._load_config()
        self.apps = self._load_apps()
        self._migrate_apps()

    def _get_config_dir(self):
        """Get configuration directory"""
        # When packaged as executable, use ~/.config/Beer/ to keep
        # the executable directory clean (only the executable itself)
        if getattr(sys, 'frozen', False):
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'Beer')
        else:
            # Running as script - use project root for development
            config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def _load_config(self):
        """Load configuration from file and migrate older formats."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                merged = dict(self.DEFAULT_CONFIG)
                merged.update(config)
                self._migrate_config(merged)
                return merged
            except Exception as e:
                print(f"Error loading config: {e}")
                return dict(self.DEFAULT_CONFIG)
        return dict(self.DEFAULT_CONFIG)

    @staticmethod
    def _migrate_config(config):
        """Migrate settings from older Beer versions in-place."""
        # V1.1 and older used a single "custom Proton path".
        old_enabled = config.pop('custom_proton_enabled', False)
        old_path = config.pop('custom_proton_path', '')
        custom_paths = list(config.get('custom_proton_paths') or [])
        if old_enabled and old_path and old_path not in custom_paths:
            custom_paths.append(old_path)
        config['custom_proton_paths'] = [p for p in custom_paths if p]

        # Remove obsolete keys that are no longer used.
        config.pop('tool_directory', None)

        if not config.get('proton_search_paths'):
            config['proton_search_paths'] = default_proton_search_paths()

        config.setdefault('log_auto_scroll', True)
        config.setdefault('wine_prefix_dir', os.path.expanduser('~/.local/share/Beer/prefixes'))
        config.setdefault('winetricks_path', '')
        config.setdefault('winetricks_verbs_cache', [])
        config.setdefault('sort_mode', 'name')

        shelves = config.get('shelves')
        if not isinstance(shelves, list) or not shelves:
            config['shelves'] = [
                {'id': 'preset:recent', 'preset': 'recent'},
                {'id': 'preset:all', 'preset': 'all'},
            ]
        else:
            shelves = [s for s in shelves if isinstance(s, dict)]
            # "Recent" must always sit directly above "All apps".
            preset_by_name = {
                s.get('preset'): s for s in shelves
                if s.get('preset') in ('all', 'recent')
            }
            preset_indexes = [
                index for index, shelf in enumerate(shelves)
                if shelf.get('preset') in ('all', 'recent')
            ]
            insert_at = min(preset_indexes) if preset_indexes else len(shelves)
            others = [
                shelf for shelf in shelves
                if shelf.get('preset') not in ('all', 'recent')
            ]
            recent = preset_by_name.get('recent') or {
                'id': 'preset:recent', 'preset': 'recent'
            }
            all_apps = preset_by_name.get('all') or {
                'id': 'preset:all', 'preset': 'all'
            }
            insert_at = min(insert_at, len(others))
            others[insert_at:insert_at] = [recent, all_apps]
            config['shelves'] = others

    def _write_json(self, path, data):
        """Write JSON atomically so concurrent readers never see a partial file."""
        temp_path = ''
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(
                dir=self.config_dir, prefix='.beer-', suffix='.json'
            )
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, path)
            return True
        except Exception as e:
            print(f"Error saving {os.path.basename(path)}: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            return False

    def _save_config(self):
        """Save configuration to file"""
        return self._write_json(self.config_file, self.config)

    def _load_apps(self):
        """Load saved applications"""
        if os.path.exists(self.apps_file):
            try:
                with open(self.apps_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return [app for app in data if isinstance(app, dict)]
            except Exception as e:
                print(f"Error loading apps: {e}")
                return []
        return []

    def _migrate_apps(self):
        """Assign stable IDs and per-application prefix paths to old entries."""
        changed = False
        for app in self.apps:
            if ensure_app_prefix_fields(self, app):
                changed = True
            for key in ('hero_image', 'logo_image'):
                if self._persist_app_image(app, key):
                    changed = True
        if changed:
            self._save_apps()

    @staticmethod
    def _now_iso():
        return datetime.datetime.now().isoformat(timespec='seconds')

    def _save_apps(self):
        """Save applications to file"""
        return self._write_json(self.apps_file, self.apps)

    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)

    def get_icons_dir(self):
        """Get persistent icons directory"""
        icons_dir = os.path.join(self.config_dir, 'icons')
        os.makedirs(icons_dir, exist_ok=True)
        return icons_dir

    def get_images_dir(self):
        """Get the directory that stores custom hero/logo images."""
        images_dir = os.path.join(self.config_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        return images_dir

    def import_image(self, source_path, app_id, kind):
        """Copy a custom image into Beer's config directory.

        Returns the stored path, or an empty string on failure.
        """
        source = expand_path(source_path)
        if not source or not os.path.isfile(source):
            return ''
        extension = os.path.splitext(source)[1].lower()
        if extension not in ('.png', '.jpg', '.jpeg', '.webp', '.bmp',
                             '.gif', '.svg'):
            extension = '.png'
        safe_id = re.sub(
            r'[^0-9A-Za-z._-]+', '-', str(app_id or 'app')
        ).strip('-._') or 'app'
        filename = '{}_{}_{}{}'.format(
            safe_id, kind, uuid.uuid4().hex[:8], extension
        )
        destination = os.path.join(self.get_images_dir(), filename)
        try:
            shutil.copy2(source, destination)
            return destination
        except OSError:
            return ''

    def _persist_app_image(self, app, key):
        """Move an app's custom image reference into the config directory."""
        current = expand_path(app.get(key, ''))
        if not current or not os.path.isfile(current):
            return False
        images_dir = os.path.realpath(self.get_images_dir())
        try:
            inside = os.path.commonpath(
                [os.path.realpath(current), images_dir]
            ) == images_dir
        except ValueError:
            inside = False
        if inside:
            return False
        kind = 'hero' if key == 'hero_image' else 'logo'
        stored = self.import_image(current, app.get('app_id', ''), kind)
        if not stored:
            return False
        app[key] = stored
        if key == 'logo_image' and app.get('icon_path') == current:
            app['icon_path'] = stored
        return True

    def get_wine_prefix_dir(self):
        """Return the configured Wine prefix directory (expanded)."""
        return expand_path(
            self.config.get('wine_prefix_dir')
            or os.path.expanduser('~/.local/share/Beer/prefixes')
        )

    def get_custom_runtime_paths(self):
        """Return configured custom Proton/Wine paths."""
        return list(self.config.get('custom_proton_paths') or [])

    # ------------------------------------------------------------------
    # Shelves (Steam-style library rows)
    # ------------------------------------------------------------------
    def get_shelves(self):
        """Return the ordered shelf list.

        Each entry has ``id``, optional ``preset`` (``all`` / ``recent``)
        and an optional custom ``name``.
        """
        shelves = self.config.get('shelves')
        if not isinstance(shelves, list) or not shelves:
            shelves = [
                {'id': 'preset:recent', 'preset': 'recent'},
                {'id': 'preset:all', 'preset': 'all'},
            ]
            self.config['shelves'] = shelves
        result = []
        for index, shelf in enumerate(shelves):
            if not isinstance(shelf, dict) or not shelf.get('id'):
                continue
            entry = dict(shelf)
            entry['order'] = index
            result.append(entry)
        return result

    def save_shelves(self, shelves):
        """Persist shelves and normalise their order."""
        normalised = []
        for index, shelf in enumerate(shelves or []):
            if not isinstance(shelf, dict) or not shelf.get('id'):
                continue
            entry = dict(shelf)
            entry['order'] = index
            normalised.append(entry)
        self.config['shelves'] = normalised
        return self._save_config()

    def add_shelf(self, name):
        """Create a custom shelf and return its entry."""
        shelves = self.get_shelves()
        existing = {shelf.get('id') for shelf in shelves}
        index = 1
        while f'custom:{index}' in existing:
            index += 1
        shelf = {'id': f'custom:{index}', 'name': name}
        # New shelves appear at the top of the library.
        shelves.insert(0, shelf)
        self.save_shelves(shelves)
        return shelf

    def rename_shelf(self, shelf_id, name):
        """Rename a custom shelf."""
        shelves = self.get_shelves()
        for shelf in shelves:
            if shelf.get('id') == shelf_id and not shelf.get('preset'):
                shelf['name'] = name
                self.save_shelves(shelves)
                return True
        return False

    def delete_shelf(self, shelf_id):
        """Delete a custom shelf and remove it from every saved app."""
        shelves = [s for s in self.get_shelves() if s.get('id') != shelf_id]
        self.save_shelves(shelves)
        changed = False
        for app in self.apps:
            memberships = app.get('shelves')
            if isinstance(memberships, list) and shelf_id in memberships:
                app['shelves'] = [s for s in memberships if s != shelf_id]
                changed = True
        if changed:
            self._save_apps()
        return True

    def move_shelf(self, shelf_id, delta):
        """Move a shelf up or down in the ordering."""
        shelves = self.get_shelves()
        index = next(
            (i for i, shelf in enumerate(shelves) if shelf.get('id') == shelf_id),
            -1,
        )
        if index < 0:
            return False
        new_index = index + delta
        if new_index < 0 or new_index >= len(shelves):
            return False
        shelf = shelves.pop(index)
        shelves.insert(new_index, shelf)
        self.save_shelves(shelves)
        return True

    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config()

    def reset_to_default(self):
        """Reset configuration to defaults"""
        self.config = dict(self.DEFAULT_CONFIG)
        self._save_config()

    def save_app(self, app_config):
        """Save an application configuration"""
        preserved = (
            'app_id', 'compat_data_path', 'wine_prefix', 'created_at',
            'legacy_prefix_prompted', 'total_runtime', 'last_launched',
            'shelves', 'hero_image', 'hero_offset', 'hero_scale',
            'logo_image', 'logo_offset', 'logo_scale', 'logo_hidden',
            'base_icon_path', 'base_icon_name', 'desktop_options',
        )
        for i, app in enumerate(self.apps):
            if app.get('name') == app_config.get('name'):
                for key in preserved:
                    if key in app and key not in app_config:
                        app_config[key] = app[key]
                self.apps[i] = app_config
                if not app_config.get('created_at'):
                    app_config['created_at'] = self._now_iso()
                ensure_app_prefix_fields(self, app_config)
                self._save_apps()
                return True

        if not app_config.get('created_at'):
            app_config['created_at'] = self._now_iso()
        ensure_app_prefix_fields(self, app_config)
        self.apps.append(app_config)
        return self._save_apps()

    def find_app_by_exe(self, exe_path):
        """Return the saved application that points at *exe_path*."""
        if not exe_path:
            return None
        target = os.path.realpath(expand_path(exe_path))
        for app in self.apps:
            current = app.get('exe_path', '')
            if current and os.path.realpath(expand_path(current)) == target:
                return app
        return None

    def unique_app_name(self, base):
        """Return a name that is not used by an existing application."""
        base = (base or 'Application').strip() or 'Application'
        names = {app.get('name') for app in self.apps}
        if base not in names:
            return base
        index = 2
        while f'{base} ({index})' in names:
            index += 1
        return f'{base} ({index})'

    def delete_app(self, app_name):
        """Delete an application configuration"""
        return self.delete_apps([app_name])

    def delete_apps(self, app_names):
        """Delete several application configurations in one write."""
        names = set(app_names or ())
        if not names:
            return True
        self.apps = [
            app for app in self.apps if app.get('name') not in names
        ]
        return self._save_apps()

    def get_apps(self):
        """Get all saved applications"""
        return self.apps

    def export_apps(self, filepath):
        """Export applications to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting apps: {e}")
            return False

    def import_apps(self, filepath):
        """Import applications from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            if isinstance(imported, list):
                existing_names = {app.get('name') for app in self.apps}
                for app in imported:
                    if not isinstance(app, dict) or not app.get('name'):
                        continue
                    if not app.get('created_at'):
                        app['created_at'] = self._now_iso()
                    ensure_app_prefix_fields(self, app)
                    if app.get('name') in existing_names:
                        for index, old in enumerate(self.apps):
                            if old.get('name') != app.get('name'):
                                continue
                            for key in ('app_id', 'compat_data_path',
                                        'wine_prefix', 'created_at'):
                                if old.get(key) and not app.get(key):
                                    app[key] = old[key]
                            self.apps[index] = app
                            break
                    else:
                        self.apps.append(app)
                        existing_names.add(app.get('name'))
                return self._save_apps()
            return False
        except Exception as e:
            print(f"Error importing apps: {e}")
            return False

    def clean_unused_images(self):
        """Delete unused icon and custom image files.

        Covers the ``icons`` and ``images`` directories and keeps any file
        referenced by a saved application.

        Returns the number of removed files.
        """
        used = set()
        for app in self.apps:
            for key in ('icon_path', 'base_icon_path',
                        'hero_image', 'logo_image'):
                value = app.get(key)
                if value:
                    used.add(os.path.abspath(value))
            desktop_icon = (app.get('desktop_options') or {}).get('icon_path')
            if desktop_icon:
                used.add(os.path.abspath(desktop_icon))

        removed = 0
        for directory in (self.get_icons_dir(), self.get_images_dir()):
            if not os.path.isdir(directory):
                continue
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if not os.path.isfile(filepath):
                    continue
                if os.path.abspath(filepath) in used:
                    continue
                try:
                    os.remove(filepath)
                    removed += 1
                except OSError as exc:
                    print(f"Error removing image {filepath}: {exc}")

        return removed
