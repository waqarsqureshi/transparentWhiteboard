from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication
import sys

from canvas.canvas import TransparentCanvas
from ui.toolbar import FloatingToolbar
from app.config import WhiteboardConfig, ConfigManager
from export.image_export import ImageExporter
from export.screenshot import ScreenshotCapture
from persistence.autosave import AutosaveManager

class TransparentWhiteboardWindow(QMainWindow):
    def __init__(self, screen_index: int = 0, config: WhiteboardConfig = None):
        super().__init__()
        self.screen_index = screen_index
        self.config = config or ConfigManager.load()

        # Frameless, Always on Top, 100% Transparent Background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Fullscreen Transparent Canvas
        self.canvas = TransparentCanvas(self)
        self.canvas.set_bg_mode("desktop")
        self.canvas.set_colour(self.config.default_color)
        self.canvas.set_width(self.config.default_width)
        self.setCentralWidget(self.canvas)

        # Compact Floating Toolbar
        self.toolbar = FloatingToolbar(self.canvas)
        self.toolbar.show()
        self.toolbar.move(self.config.toolbar_position[0], self.config.toolbar_position[1])

        self._position_on_screen()
        self._connect_signals()
        self._setup_shortcuts()

        # Autosave manager
        self.autosave = AutosaveManager(get_strokes_callback=lambda: self.canvas.strokes, parent=self)
        self.autosave.configure(self.config.enable_autosave, self.config.autosave_interval_minutes)

    def _position_on_screen(self):
        screens = QGuiApplication.screens()
        screen = screens[self.screen_index] if 0 <= self.screen_index < len(screens) else QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
            self.resize(geo.size())

    def apply_fullscreen_geometry(self):
        screens = QGuiApplication.screens()
        screen = screens[self.screen_index] if 0 <= self.screen_index < len(screens) else QGuiApplication.primaryScreen()
        if not screen: return
        geo = screen.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        self.setGeometry(x, y, w, h)
        self.resize(w, h)
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.setGeometry(0, 0, w, h)
            self.canvas.resize(w, h)
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = int(self.winId())
                if self.screen_index == 0:
                    sm_w, sm_h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
                    if sm_w > w: w = sm_w
                    if sm_h > h: h = sm_h
                user32.SetWindowPos(hwnd, -1, x, y, w, h, 0x0040 | 0x0020)
            except Exception as e:
                print(f"SetWindowPos error: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_fullscreen_geometry()
        QTimer.singleShot(50, self.apply_fullscreen_geometry)
        QTimer.singleShot(250, self.apply_fullscreen_geometry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.resize(self.size())
        if hasattr(self, 'toolbar') and hasattr(self, 'canvas'):
            tb_x = min(self.toolbar.x(), max(10, self.canvas.width() - self.toolbar.width() - 20))
            tb_y = min(self.toolbar.y(), max(10, self.canvas.height() - self.toolbar.height() - 20))
            self.toolbar.move(max(10, tb_x), max(10, tb_y))

    def _connect_signals(self):
        self.toolbar.tool_changed.connect(self.canvas.set_tool)
        self.toolbar.color_changed.connect(self.canvas.set_colour)
        self.toolbar.width_changed.connect(self.canvas.set_width)
        self.toolbar.undo_requested.connect(self.canvas.undo)
        self.toolbar.redo_requested.connect(self.canvas.redo)
        self.toolbar.clear_requested.connect(self.canvas.clear)
        self.toolbar.save_annotation_requested.connect(self.save_annotations_dialog)
        self.toolbar.save_screenshot_requested.connect(self.save_screenshot_dialog)
        self.toolbar.exit_requested.connect(self.close)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_annotations_dialog)
        QShortcut(QKeySequence("Delete"), self, activated=self.canvas.clear)
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.close)
        QShortcut(QKeySequence("Alt+F4"), self, activated=self.close)

    def save_annotations_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Transparent Annotations", "whiteboard_annotations.png", "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        if file_path:
            fmt = "PNG" if file_path.lower().endswith(".png") else "JPEG"
            geo = self.canvas.size()
            success = ImageExporter.export_annotations_to_file(
                file_path=file_path,
                strokes=self.canvas.strokes,
                width=geo.width(),
                height=geo.height(),
                format_name=fmt,
                transparent=(fmt == "PNG"),
            )
            if success:
                QMessageBox.information(self, "Export Successful", f"Saved annotations to:\n{file_path}")

    def save_screenshot_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Combined Screenshot", "whiteboard_screenshot.png", "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        if file_path:
            self.toolbar.hide()
            QTimer.singleShot(150, lambda: self._perform_screenshot_capture(file_path))

    def _perform_screenshot_capture(self, file_path: str):
        pixmap = ScreenshotCapture.capture_desktop_with_annotations(
            strokes=self.canvas.strokes, screen_index=self.screen_index
        )
        self.toolbar.show()
        if pixmap and not pixmap.isNull():
            success = pixmap.save(file_path)
            if success:
                QMessageBox.information(self, "Saved", f"Combined screenshot saved to:\n{file_path}")

    def closeEvent(self, event):
        pos = self.toolbar.pos()
        self.config.toolbar_position = [pos.x(), pos.y()]
        ConfigManager.save(self.config)
        super().closeEvent(event)
