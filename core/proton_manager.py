# -*- coding: utf-8 -*-
"""
Proton version manager for Beer
"""

import os
import subprocess
from pathlib import Path


class ProtonManager:
    """Manages Proton installations"""
    
    def __init__(self, search_paths=None):
        self.search_paths = search_paths or [
            os.path.expanduser('~/.steam/steam/steamapps/common/'),
            os.path.expanduser('~/.local/share/Steam/steamapps/common/')
        ]
        self.proton_versions = []
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
        # Remove 'Proton-' prefix if present
        if name.startswith('Proton-'):
            name = name[7:]
        
        # Try to parse version
        parts = name.split('.')
        version_parts = []
        
        for part in parts:
            # Extract numeric part
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
        # Try to find Steam installation
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
    
    def launch_program(self, proton_path, exe_path, working_dir=None, env_vars=None, args=None):
        """Launch a Windows program using Proton"""
        if not os.path.exists(exe_path):
            return False, "Executable not found"
        
        proton_script = os.path.join(proton_path, 'proton')
        if not os.path.exists(proton_script):
            return False, "Proton script not found"
        
        # Build command
        env = os.environ.copy()
        
        # Set Steam compatibility paths
        compat_paths = self.get_steam_compat_paths(proton_path)
        if compat_paths:
            env.update(compat_paths)
        
        # Add custom environment variables
        if env_vars:
            env.update(env_vars)
        
        # Build command arguments
        cmd = [proton_script, 'run', exe_path]
        
        if args:
            cmd.extend(args)
        
        # Set working directory
        cwd = working_dir or os.path.dirname(exe_path)
        
        try:
            # 不使用 PIPE，让子进程完全独立运行
            # 使用 start_new_session 创建新会话，使子进程脱离父进程
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=cwd,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True, process
        except Exception as e:
            return False, str(e)
