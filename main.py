"""
Transparent Windows Digital Whiteboard
======================================
Entry point for the Windows desktop application.
Initializes PySide6, applies Windows DPI awareness, and launches
either the startup launcher dialog or the fullscreen transparent whiteboard canvas.
"""

import sys
import os
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.application import WhiteboardApplication
from app.config import ConfigManager
from ui.launcher_dialog import LauncherDialog
from ui.main_window import TransparentWhiteboardWindow


def parse_arguments():
    parser = argparse.ArgumentParser(description="Transparent Windows Digital Whiteboard")
    parser.add_argument(
        "--launcher",
        action="store_true",
        help="Open startup display picker dialog before starting whiteboard",
    )
    parser.add_argument(
        "--display",
        type=int,
        default=None,
        help="Screen index to launch annotation canvas on (0 = primary)",
    )
    return parser.parse_args()


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    app = WhiteboardApplication(sys.argv)
    app.setApplicationName("Transparent Whiteboard")
    app.setOrganizationName("WhiteboardDev")

    args = parse_arguments()
    config = ConfigManager.load()

    screen_index = args.display if args.display is not None else config.selected_display

    if args.launcher:
        launcher = LauncherDialog(config=config)
        if launcher.exec():
            screen_index = launcher.get_selected_display()
        else:
            return 0

    window = TransparentWhiteboardWindow(screen_index=screen_index, config=config)
    window.showMaximized()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
