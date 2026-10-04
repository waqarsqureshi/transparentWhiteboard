# Transparent Windows Digital Whiteboard

A transparent annotation layer for your desktop with touch, pen, and stylus support.
Draw on top of any app, switch between apps freely, and save your strokes along with the screen.

## Why this exists

As an instructor, I always wanted an app that lets me use a pencil or marker directly on
the screen I'm sharing, while still switching between apps. I also wanted to save the
strokes together with the shared screen, or mark up anything on my current desktop.

PowerPoint offers inking, but it is restricted to the app itself. This tool works as a
transparent layer over your whole desktop, so you can annotate any window, such as slides,
code editors, browsers, or PDFs, without leaving it.

## Platform support

| Platform | How to run |
|----------|------------|
| Windows 10 / 11 | Download the ready-made release from GitHub Releases, or run from source |
| Linux | Run from source |
| macOS | Run from source |

## Run from source

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Helper scripts (`.bat` and `.ps1`)

This repository includes Windows helper scripts to make common tasks easier.

### What the scripts do

- **`.bat` (Batch script)**  
  A Windows Command Prompt script. Use this when working in `cmd.exe` or for double-click execution.

- **`.ps1` (PowerShell script)**  
  A PowerShell script with richer scripting support. Use this in PowerShell (`pwsh` / Windows PowerShell).

These scripts are typically used to:
- set up a Python environment,
- install dependencies,
- run the app,
- and/or package builds.

### Which one should I use?

- Use **`.bat`** if you prefer Command Prompt or simple double-click execution.
- Use **`.ps1`** if you prefer PowerShell and more flexible scripting.

## Build

### Linux / macOS

Use the build helper script:

```bash
python3 build.py
```

This is the recommended way to build on Linux or macOS.

### Windows

Use the provided `.bat` or `.ps1` script, or run equivalent manual build commands.

## Build a Windows `.exe` from Ubuntu (PyInstaller)

> You likely meant **PyInstaller** (packaging), not **Pylance** (VS Code language server).

Native Windows `.exe` files are most reliable when built on Windows.  
If you're on Ubuntu, the recommended path is to build on a Windows GitHub Actions runner.

### Recommended: GitHub Actions on Windows

```yaml
name: Build Windows EXE

on:
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build EXE
        run: |
          pyinstaller --onefile --windowed main.py --name transparent-whiteboard

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: transparent-whiteboard-windows
          path: dist/transparent-whiteboard.exe
```

### Local Ubuntu build note

If you run PyInstaller directly on Ubuntu, it builds a Linux binary (not a Windows `.exe`).
