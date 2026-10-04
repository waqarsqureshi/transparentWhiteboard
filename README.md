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
| Linux | Run the Python version from source |
| macOS | Run the Python version from source |

## Run from source

```powershell
python -m pip install -r requirements.txt
python main.py
```
## Helper scripts (`.bat` and `.ps1`)

This repository includes Windows helper scripts to make common tasks easier.

### What the scripts do

- **`.bat` (Batch script)**  
  A classic Windows Command Prompt script.  
  Use this when you want a double-clickable script or when working in `cmd.exe`.

- **`.ps1` (PowerShell script)**  
  A PowerShell script with better scripting features (error handling, parameters, richer commands).  
  Use this if you run tasks from PowerShell (`pwsh` / Windows PowerShell).

Typical script responsibilities in this project include:
- setting up a local Python environment,
- installing dependencies,
- running the app,
- and/or packaging builds.

> Open each script to see exact commands and edit paths/options as needed for your machine.

### Which one should I use?

- Use **`.bat`** if you prefer Command Prompt or simple double-click execution.
- Use **`.ps1`** if you prefer PowerShell and more flexible scripting.

---

## Build a Windows `.exe` from Ubuntu (PyInstaller)

> Note: Native Windows `.exe` files generally need to be built on Windows for best compatibility.  
> On Ubuntu/Linux, you can reliably build Linux binaries. Building a true Windows `.exe` on Linux is usually done with a Windows CI runner or Wine-based workflows.

### Recommended approach (cross-platform CI)

Use **GitHub Actions** with a Windows runner:

1. Push your code to GitHub.
2. Add a workflow that runs on `windows-latest`.
3. Install dependencies and run PyInstaller there.
4. Upload the produced `.exe` as an artifact or release asset.

Minimal workflow example:

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

### Local Ubuntu build (Linux binary only)

If you are building *on Ubuntu itself*, this builds a Linux executable, not a Windows `.exe`:

```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed main.py --name transparent-whiteboard
```

Output:
- Linux binary at `dist/transparent-whiteboard`

---

## Notes on “Pylance” vs “PyInstaller”

- **Pylance** = VS Code language/intellisense extension (does not build executables)
- **PyInstaller** = packaging tool used to create standalone executables
