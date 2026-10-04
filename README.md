# Transparent Windows Digital Whiteboard

A transparent annotation layer for Windows 10 and 11 with touch, pen, and stylus support.

## Run from source

```powershell
python -m pip install -r requirements.txt
python main.py
```

Pass `--launcher` to choose a display before opening the whiteboard, or `--display N`
to select a display directly (the primary display is `0`).

## Build for Windows

```powershell
python build_exe.py
```

The distributable folder is `dist/TransparentWhiteboard/`. Keep the entire folder
together when running or sharing the application; the executable depends on files
alongside it. A ZIP of this folder is provided in the repository's GitHub Releases.
