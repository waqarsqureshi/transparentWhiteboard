#!/usr/bin/env python3
"""
Build script for Transparent Windows Digital Whiteboard.
Automates running PyInstaller, verifying output, and generating the distribution folder.
Usage:
    python build_exe.py
"""

import os
import sys
import subprocess
import shutil


def build():
    print("=" * 60)
    print("Transparent Whiteboard - Standalone Windows Executable Builder")
    print("=" * 60)

    # 1. Verify dependencies
    try:
        import PySide6
        import PyInstaller
    except ImportError as e:
        print()
        print(f"[ERROR] Missing required build tool: {e}")
        print("Please install requirements first:")
        print("    pip install -r requirements.txt")
        sys.exit(1)

    spec_file = "TransparentWhiteboard.spec"
    if not os.path.exists(spec_file):
        print()
        print(f"[ERROR] {spec_file} was not found in the current directory.")
        sys.exit(1)

    print()
    print("[1/3] Running PyInstaller build...")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "-y", spec_file]
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print()
        print("[ERROR] PyInstaller build failed with exit code: " + str(result.returncode))
        sys.exit(result.returncode)

    output_dir = os.path.join("dist", "TransparentWhiteboard")
    exe_path = os.path.join(output_dir, "TransparentWhiteboard.exe")

    print()
    print("[2/3] Verifying generated package...")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"[OK] Success! Executable found at: {exe_path} ({size_mb:.1f} MB)")
    else:
        print(f"[WARNING] {exe_path} was not created in output directory.")
        sys.exit(1)

    print()
    print("[3/3] Copying README and documentation...")
    if os.path.exists("README.md"):
        shutil.copy("README.md", os.path.join(output_dir, "README.txt"))

    print()
    print("=" * 60)
    print("Build Complete! The application is ready in:")
    print(os.path.abspath(output_dir))
    print("=" * 60)


if __name__ == "__main__":
    build()
