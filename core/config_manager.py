# -*- coding: utf-8 -*-
"""
Configuration manager for Beer
"""

import json
import os
from pathlib import Path


class ConfigManager:
    """Manages application configuration"""
    
    DEFAULT_CONFIG = {
        'language': 'system',
        'theme': 'system',
        'default_page': 'main',
        'custom_proton_enabled': False,
        'custom_proton_path': '',
        'tool_directory': '',
        'proton_search_paths': [
            os.path.expanduser('~/.steam/steam/steamapps/common/'),
            os.path.expanduser('~/.local/share/Steam/steamapps/common/')
        ],
        'environment_variables': {},
    }
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.apps_file = os.path.join(self.config_dir, 'apps.json')
        self.config = self._load_config()
        self.apps = self._load_apps()
    
    def _get_config_dir(self):
        """Get configuration directory (same as executable)"""
        # Use the directory where the script is located
        if getattr(os.sys, 'frozen', False):
            # Running as compiled executable
            return os.path.dirname(os.sys.executable)
        else:
            # Running as script
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults
                    merged = self.DEFAULT_CONFIG.copy()
                    merged.update(config)
                    return merged
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def _load_apps(self):
        """Load saved applications"""
        if os.path.exists(self.apps_file):
            try:
                with open(self.apps_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading apps: {e}")
                return []
        return []
    
    def _save_apps(self):
        """Save applications to file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.apps_file, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving apps: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config()
    
    def reset_to_default(self):
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        self._save_config()
    
    def save_app(self, app_config):
        """Save an application configuration"""
        # Check if app already exists
        for i, app in enumerate(self.apps):
            if app.get('name') == app_config.get('name'):
                self.apps[i] = app_config
                self._save_apps()
                return True
        
        # Add new app
        self.apps.append(app_config)
        return self._save_apps()
    
    def delete_app(self, app_name):
        """Delete an application configuration"""
        self.apps = [app for app in self.apps if app.get('name') != app_name]
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
                    self.apps.extend(imported)
                    return self._save_apps()
            return False
        except Exception as e:
            print(f"Error importing apps: {e}")
            return False
