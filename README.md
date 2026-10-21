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
| Windows 10 / 11 | Supported: download a release or run from source |
| Linux / macOS | Not officially supported or tested |

## Run from source

On Windows, install the dependencies and start the application:

```powershell
python -m pip install -r requirements.txt
python main.py
```

PySide6 is cross-platform, but this application also uses Windows APIs for features
such as global shortcuts and window/display behavior. Those calls are guarded so they
are not made on other platforms, but Linux and macOS behavior has not been validated
and may differ.

## Helper scripts (`.bat` and `.ps1`)

This repository includes Windows helper scripts to install dependencies and build the
application.

### What the scripts do

- **`.bat` (Batch script)**  
  A Windows Command Prompt script. Use this when working in `cmd.exe` or for double-click execution.

- **`.ps1` (PowerShell script)**  
  A PowerShell script with richer scripting support. Use this in PowerShell (`pwsh` / Windows PowerShell).

### Which one should I use?

- Use **`.bat`** if you prefer Command Prompt or simple double-click execution.
- Use **`.ps1`** if you prefer PowerShell and more flexible scripting.

## Build

### Windows

Run `.\build.ps1` in PowerShell or `build.bat` in Command Prompt. Both scripts install
the requirements and build with `TransparentWhiteboard.spec`. The standalone
application is created at
`dist\TransparentWhiteboard\TransparentWhiteboard.exe`.

### Linux / macOS

Linux and macOS builds are not supported or tested. PyInstaller packages for the
operating system on which it runs; running it on Linux does not produce a Windows
`.exe`. Build Windows executables on Windows, including on a Windows CI runner.
