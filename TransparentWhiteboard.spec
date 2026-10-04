# -*- mode: python ; coding: utf-8 -*-
# PyInstaller specification for Transparent Windows Digital Whiteboard
# Builds a standalone Windows 64-bit application folder

import sys
import os

conda_library_bin = os.path.join(sys.prefix, 'Library', 'bin')
if os.path.isdir(conda_library_bin):
    os.environ['PATH'] = os.pathsep.join(
        [conda_library_bin, os.environ.get('PATH', '')]
    )

block_cipher = None
project_dir = os.path.abspath(os.path.dirname(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        ('app', 'app'),
        ('canvas', 'canvas'),
        ('ui', 'ui'),
        ('commands', 'commands'),
        ('export', 'export'),
        ('persistence', 'persistence'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'win32api',
        'win32gui',
        'win32con',
        'ctypes',
        'ctypes.wintypes',
    ],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TransparentWhiteboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TransparentWhiteboard',
)
