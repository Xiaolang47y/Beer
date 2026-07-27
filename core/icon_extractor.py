# -*- coding: utf-8 -*-
"""
Icon extractor for Windows executables
"""

import os
import shutil
import hashlib
from pathlib import Path


class IconExtractor:
    """Extracts icons from Windows executables"""

    # Cache tool availability at class level to avoid repeated subprocess calls
    _tools_cache = None

    def __init__(self, tool_directory=None, icons_dir=None):
        self.tool_directory = tool_directory
        # Persistent storage for extracted icons
        self.icons_dir = icons_dir or os.path.join(
            os.path.expanduser('~'), '.config', 'Beer', 'icons'
        )
        os.makedirs(self.icons_dir, exist_ok=True)
        self.available_tools = self._check_available_tools()

    @classmethod
    def _check_available_tools(cls):
        """Check which icon extraction tools are available (cached)"""
        if cls._tools_cache is not None:
            return cls._tools_cache.copy()

        tools = {
            'wrest': False,
            'extract-icon': False,
            'pefile': False
        }

        # Check wrest (from ImageMagick) - only if not in a flatpak/snap
        try:
            import subprocess
            result = subprocess.run(['wrest', '-h'], capture_output=True, timeout=3)
            tools['wrest'] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check extract-icon
        try:
            import subprocess
            result = subprocess.run(['extract-icon', '--help'], capture_output=True, timeout=3)
            tools['extract-icon'] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check pefile (Python library)
        try:
            import pefile
            tools['pefile'] = True
        except ImportError:
            pass

        cls._tools_cache = tools
        return tools.copy()

    def is_tool_available(self):
        """Check if any icon extraction tool is available"""
        return any(self.available_tools.values())

    def _get_persistent_path(self, exe_path):
        """Get a persistent output path for an exe's icon"""
        # Use hash of exe path to create unique filename
        path_hash = hashlib.md5(exe_path.encode('utf-8')).hexdigest()[:8]
        base_name = os.path.splitext(os.path.basename(exe_path))[0]
        return os.path.join(self.icons_dir, f"{base_name}_{path_hash}.png")

    def extract_icon(self, exe_path, output_path=None):
        """Extract icon from executable.

        If output_path is None, the icon is saved to a persistent location
        so it survives restarts (fixes icon disappearing after reboot).
        """
        if not os.path.exists(exe_path):
            return None, "Executable not found"

        if not self.is_tool_available():
            return None, "No icon extraction tool available"

        # Use persistent path by default
        if output_path is None:
            output_path = self._get_persistent_path(exe_path)

        # Return cached icon if already extracted
        if os.path.exists(output_path):
            return output_path, None

        # Try extraction methods in order of preference
        if self.available_tools.get('pefile'):
            success, result = self._extract_with_pefile(exe_path, output_path)
            if success:
                return output_path, None

        if self.available_tools.get('wrest'):
            success, result = self._extract_with_wrest(exe_path, output_path)
            if success:
                return output_path, None

        if self.available_tools.get('extract-icon'):
            success, result = self._extract_with_extract_icon(exe_path, output_path)
            if success:
                return output_path, None

        return None, "Failed to extract icon"

    def _extract_with_pefile(self, exe_path, output_path):
        """Extract icon using pefile library"""
        try:
            import pefile
            from PIL import Image
            import struct
            import io

            pe = pefile.PE(exe_path, fast_load=True)
            pe.parse_data_directories()

            if not hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
                return False, "No resources found"

            # First, find RT_GROUP_ICON to get icon directory info
            icon_dir_data = None
            for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                if entry.id == pefile.RESOURCE_TYPE['RT_GROUP_ICON']:
                    for resource in entry.directory.entries:
                        for resource_entry in resource.directory.entries:
                            data_rva = resource_entry.data.struct.OffsetToData
                            size = resource_entry.data.struct.Size
                            icon_dir_data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
                            break
                        if icon_dir_data:
                            break
                    break

            if not icon_dir_data:
                return False, "No icon group found"

            # Parse GRPICONDIR header (6 bytes) + GRPICONDIRENTRY (14 bytes each)
            reserved, icon_type, count = struct.unpack_from('<HHH', icon_dir_data, 0)

            # Collect individual icon images
            icon_images = []
            offset = 6

            for i in range(count):
                if offset + 14 > len(icon_dir_data):
                    break
                width, height, color_count, reserved2, planes, bit_count, bytes_in_res, icon_id = struct.unpack_from('<BBBBHHIH', icon_dir_data, offset)
                offset += 14

                # Find the actual icon data by RT_ICON ID
                icon_data = None
                for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                    if entry.id == pefile.RESOURCE_TYPE['RT_ICON']:
                        for resource in entry.directory.entries:
                            if resource.id == icon_id:
                                for resource_entry in resource.directory.entries:
                                    data_rva = resource_entry.data.struct.OffsetToData
                                    size = resource_entry.data.struct.Size
                                    icon_data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
                                    break
                                break
                        if icon_data:
                            break

                if icon_data:
                    icon_images.append({
                        'width': width if width > 0 else 256,
                        'height': height if height > 0 else 256,
                        'color_count': color_count,
                        'planes': planes,
                        'bit_count': bit_count,
                        'bytes_in_res': bytes_in_res,
                        'data': icon_data
                    })

            if not icon_images:
                return False, "No icon images found"

            # Build a valid ICO file in memory
            ico_buf = io.BytesIO()
            ico_buf.write(struct.pack('<HHH', 0, 1, len(icon_images)))

            img_offset = 6 + 16 * len(icon_images)
            for img in icon_images:
                ico_buf.write(struct.pack('<BBBBHHII',
                    img['width'] & 0xFF,
                    img['height'] & 0xFF,
                    img['color_count'],
                    0,
                    img['planes'],
                    img['bit_count'],
                    img['bytes_in_res'],
                    img_offset
                ))
                img_offset += img['bytes_in_res']

            for img in icon_images:
                ico_buf.write(img['data'])

            # Free PE resources before image conversion
            pe.close()
            del pe

            # Convert ICO to PNG
            ico_buf.seek(0)
            img = Image.open(ico_buf)

            # Get the largest size
            sizes = []
            try:
                current = img.size
                sizes.append(current)
                while True:
                    img.seek(img.tell() + 1)
                    sizes.append(img.size)
            except EOFError:
                pass

            if sizes:
                largest = max(sizes, key=lambda s: s[0] * s[1])
                img.seek(0)
                for i, s in enumerate(sizes):
                    if s == largest:
                        img.seek(i)
                        break

            img.save(output_path, 'PNG')
            return True, None

        except Exception as e:
            return False, str(e)

    def _extract_with_wrest(self, exe_path, output_path):
        """Extract icon using wrest (ImageMagick)"""
        try:
            import subprocess
            ico_path = output_path.replace('.png', '.ico')

            result = subprocess.run(
                ['wrest', '-o', ico_path, exe_path],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(ico_path):
                result = subprocess.run(
                    ['convert', ico_path, output_path],
                    capture_output=True,
                    timeout=30
                )

                if result.returncode == 0:
                    os.remove(ico_path)
                    return True, None
                else:
                    os.remove(ico_path)

            return False, "wrest extraction failed"
        except Exception as e:
            return False, str(e)

    def _extract_with_extract_icon(self, exe_path, output_path):
        """Extract icon using extract-icon tool"""
        try:
            import subprocess
            result = subprocess.run(
                ['extract-icon', exe_path, output_path],
                capture_output=True,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(output_path):
                return True, None

            return False, "extract-icon failed"
        except Exception as e:
            return False, str(e)
