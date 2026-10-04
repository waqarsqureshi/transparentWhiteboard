# Transparent Windows Digital Whiteboard

A transparent annotation layer for your desktop with touch, pen, and stylus support.

Draw on top of any app, switch between apps freely, and save your strokes with the screen.

## Platform support

| Platform | How to run |
|----------|------------|
| Windows 10 / 11 | Download the release from GitHub Releases or run from source |
| Linux | Run the Python version from source |
| macOS | Run the Python version from source |

## Run from source

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Windows helper scripts

This repo includes `.bat` and `.ps1` scripts for common tasks.

- `.bat` = Command Prompt / double-click use
- `.ps1` = PowerShell with more features

## Build notes

- Building on Ubuntu produces a Linux binary, not a Windows `.exe`

## PyInstaller vs Pylance

- **PyInstaller** builds executables
- **Pylance** is a VS Code language extension
