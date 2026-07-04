# -*- coding: utf-8 -*-
"""
Icon extractor for Windows executables
"""

import os
import subprocess
import tempfile
from pathlib import Path


class IconExtractor:
    """Extracts icons from Windows executables"""
    
    def __init__(self, tool_directory=None):
        self.tool_directory = tool_directory
        self.available_tools = self._check_available_tools()
    
    def _check_available_tools(self):
        """Check which icon extraction tools are available"""
        tools = {
            'wrest': False,
            'extract-icon': False,
            'pefile': False
        }
        
        # Check wrest (from ImageMagick)
        try:
            result = subprocess.run(['wrest', '-h'], capture_output=True, timeout=5)
            tools['wrest'] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check extract-icon
        try:
            result = subprocess.run(['extract-icon', '--help'], capture_output=True, timeout=5)
            tools['extract-icon'] = True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check pefile (Python library)
        try:
            import pefile
            tools['pefile'] = True
        except ImportError:
            pass
        
        return tools
    
    def is_tool_available(self):
        """Check if any icon extraction tool is available"""
        return any(self.available_tools.values())
    
    def extract_icon(self, exe_path, output_path=None):
        """Extract icon from executable"""
        if not os.path.exists(exe_path):
            return None, "Executable not found"
        
        if not self.is_tool_available():
            return None, "No icon extraction tool available"
        
        # Determine output path
        if output_path is None:
            output_path = os.path.join(
                tempfile.gettempdir(),
                os.path.splitext(os.path.basename(exe_path))[0] + '.png'
            )
        
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
            
            pe = pefile.PE(exe_path)
            
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
                            icon_dir_data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
                            break
                        if icon_dir_data:
                            break
                    break
            
            if not icon_dir_data:
                return False, "No icon group found"
            
            # Parse GRPICONDIR header (6 bytes) + GRPICONDIRENTRY (14 bytes each)
            # GRPICONDIR: Reserved(2) + Type(2) + Count(2)
            reserved, icon_type, count = struct.unpack_from('<HHH', icon_dir_data, 0)
            
            # Collect individual icon images
            icon_images = []
            offset = 6  # Start after GRPICONDIR header
            
            for i in range(count):
                # GRPICONDIRENTRY: Width(1) + Height(1) + ColorCount(1) + Reserved(1) + Planes(2) + BitCount(2) + BytesInRes(4) + ID(2)
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
                                    icon_data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
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
            
            # Build a valid ICO file
            ico_path = output_path.replace('.png', '.ico')
            with open(ico_path, 'wb') as f:
                # ICO header
                f.write(struct.pack('<HHH', 0, 1, len(icon_images)))
                
                # Icon directory entries
                img_offset = 6 + 16 * len(icon_images)
                for img in icon_images:
                    f.write(struct.pack('<BBBBHHII',
                        img['width'] & 0xFF,
                        img['height'] & 0xFF,
                        img['color_count'],
                        0,  # reserved
                        img['planes'],
                        img['bit_count'],
                        img['bytes_in_res'],
                        img_offset
                    ))
                    img_offset += img['bytes_in_res']
                
                # Icon image data
                for img in icon_images:
                    f.write(img['data'])
            
            # Convert ICO to PNG
            try:
                img = Image.open(ico_path)
                # Get the largest size
                sizes = []
                try:
                    while True:
                        img.seek(img.tell() + 1)
                        sizes.append(img.size)
                except EOFError:
                    pass
                
                if sizes:
                    # Find largest icon
                    largest = max(sizes, key=lambda s: s[0] * s[1])
                    img.seek(0)
                    for i, s in enumerate([img.size] + sizes):
                        if s == largest:
                            img.seek(i)
                            break
                
                img.save(output_path, 'PNG')
                os.remove(ico_path)
                return True, None
            except Exception as e:
                if os.path.exists(ico_path):
                    os.remove(ico_path)
                return False, f"PNG conversion failed: {e}"
                
        except Exception as e:
            return False, str(e)
    
    def _extract_with_wrest(self, exe_path, output_path):
        """Extract icon using wrest (ImageMagick)"""
        try:
            # Extract icon to ICO format first
            ico_path = output_path.replace('.png', '.ico')
            
            result = subprocess.run(
                ['wrest', '-o', ico_path, exe_path],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(ico_path):
                # Convert ICO to PNG using ImageMagick
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
