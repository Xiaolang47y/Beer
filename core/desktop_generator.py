# -*- coding: utf-8 -*-
"""
Desktop file generator for Beer
"""

import os
import subprocess


class DesktopGenerator:
    """Generates .desktop files for Linux"""
    
    def __init__(self):
        self.desktop_dir = self._get_desktop_dir()
    
    def _get_desktop_dir(self):
        """Detect desktop directory (supports Chinese locale)"""
        # Try xdg-user-dir first
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
        
        # Fallback: check common paths
        home = os.path.expanduser('~')
        for name in ['Desktop', '桌面']:
            path = os.path.join(home, name)
            if os.path.isdir(path):
                return path
        
        # Last resort
        return os.path.join(home, 'Desktop')
    
    def generate_desktop_file(self, name, exe_path, icon_path=None, working_dir=None, 
                              proton_path=None, env_vars=None, args=None, comment=None):
        """Generate a .desktop file"""
        
        # Ensure desktop dir exists
        os.makedirs(self.desktop_dir, exist_ok=True)
        
        # Build command
        if proton_path:
            proton_script = os.path.join(proton_path, 'proton')
            
            # Build env prefix
            env_parts = []
            
            # Add Steam compat paths
            steam_compat = self._get_steam_compat_paths(proton_path)
            if steam_compat:
                for key, value in steam_compat.items():
                    env_parts.append(f'{key}="{value}"')
            
            # Add custom environment variables
            if env_vars:
                for key, value in env_vars.items():
                    env_parts.append(f'{key}="{value}"')
            
            if env_parts:
                command = 'env ' + ' '.join(env_parts) + f' "{proton_script}" run "{exe_path}"'
            else:
                command = f'"{proton_script}" run "{exe_path}"'
        else:
            command = f'"{exe_path}"'
        
        # Add arguments
        if args:
            command += ' ' + ' '.join(f'"{a}"' for a in args)
        
        # Build desktop file content
        lines = [
            '[Desktop Entry]',
            'Version=1.0',
            'Type=Application',
            f'Name={name}',
            f'Comment={comment or name}',
            f'Exec={command}',
        ]
        
        if working_dir:
            lines.append(f'Path={working_dir}')
        
        if icon_path and os.path.exists(icon_path):
            lines.append(f'Icon={icon_path}')
        else:
            lines.append('Icon=application-x-executable')
        
        lines.append('Terminal=false')
        lines.append('Categories=Game;')
        lines.append('StartupNotify=true')
        lines.append('')  # trailing newline
        
        desktop_content = '\n'.join(lines)
        
        # Write desktop file
        safe_name = name.replace(' ', '_').replace('/', '_')
        desktop_filename = f"{safe_name}.desktop"
        desktop_path = os.path.join(self.desktop_dir, desktop_filename)
        
        try:
            with open(desktop_path, 'w', encoding='utf-8') as f:
                f.write(desktop_content)
            
            # Make executable and trusted
            os.chmod(desktop_path, 0o755)
            
            # Try to mark as trusted via gio (for GNOME-based DEs)
            try:
                subprocess.run(
                    ['gio', 'set', desktop_path, 'metadata::trusted', 'true'],
                    capture_output=True, timeout=5
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            return True, desktop_path
        except Exception as e:
            return False, str(e)
    
    def _get_steam_compat_paths(self, proton_path):
        """Get Steam compatibility environment variables"""
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
    
    def delete_desktop_file(self, name):
        """Delete a .desktop file"""
        safe_name = name.replace(' ', '_').replace('/', '_')
        desktop_filename = f"{safe_name}.desktop"
        desktop_path = os.path.join(self.desktop_dir, desktop_filename)
        
        if os.path.exists(desktop_path):
            try:
                os.remove(desktop_path)
                return True
            except Exception:
                return False
        return True
