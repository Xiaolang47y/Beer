#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for Beer - package as executable with PyInstaller.

Use ``python3 build.py`` for a single executable and ``python3 build.py
--appimage`` (or ``bash build_appimage.sh``) to create the V1.2 AppImage.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from core.version import APP_VERSION, APP_VERSION_LABEL


def ensure_pyinstaller():
    import importlib.util

    if importlib.util.find_spec('PyInstaller') is not None:
        return True

    print("PyInstaller not found. Installing...")
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', 'pyinstaller']
        )
    except subprocess.CalledProcessError:
        return False
    return importlib.util.find_spec('PyInstaller') is not None


def build():
    """Build Beer as a single executable."""
    print(f"Building Beer {APP_VERSION_LABEL} executable...")

    if not ensure_pyinstaller():
        print("PyInstaller is required to build Beer.")
        sys.exit(1)

    for directory in ('build', 'dist'):
        path = Path(directory)
        if path.exists():
            shutil.rmtree(path)

    icon_args = []
    icon = Path('assets/beer.png')
    if icon.exists():
        icon_args = [f'--icon={icon}']

    args = [
        sys.executable, '-m', 'PyInstaller',
        '--name=Beer',
        '--onefile',
        '--windowed',
        '--noconfirm',
        '--clean',
        '--add-data', 'assets:assets',
        *icon_args,
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
    print(f"Size: {exe_path.stat().st_size / (1024 * 1024):.2f} MB")
    print("Build complete!")


def build_appimage():
    """Run the AppImage packaging script."""
    script = Path('build_appimage.sh')
    if not script.exists():
        print("build_appimage.sh was not found!")
        sys.exit(1)
    env = os.environ.copy()
    env.setdefault('VERSION', APP_VERSION)
    sys.exit(subprocess.call(['bash', str(script)], env=env))


def main():
    parser = argparse.ArgumentParser(description='Build Beer')
    parser.add_argument(
        '--appimage', action='store_true',
        help='Build a portable AppImage after creating the executable'
    )
    args = parser.parse_args()

    if args.appimage:
        build_appimage()
    else:
        build()
        print(
            'Tip: run "bash build_appimage.sh" or '
            '"python3 build.py --appimage" to create Beer-'
            f'{APP_VERSION_LABEL}-x86_64.AppImage'
        )


if __name__ == '__main__':
    main()
