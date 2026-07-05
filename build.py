#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for Beer - Package as executable using PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path


def build():
    """Build Beer as executable"""
    print("Building Beer executable...")

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Clean previous build
    for d in ['build', 'dist']:
        p = Path(d)
        if p.exists():
            import shutil
            shutil.rmtree(p)

    # PyInstaller arguments
    args = [
        sys.executable, '-m', 'PyInstaller',
        '--name=Beer',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        'main.py'
    ]

    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args)

    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    exe_path = Path('dist/Beer')
    if not exe_path.exists():
        print("Executable not found after build!")
        sys.exit(1)

    print(f"Executable created: {exe_path}")
    print(f"Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
    print("Build complete!")


if __name__ == '__main__':
    build()
