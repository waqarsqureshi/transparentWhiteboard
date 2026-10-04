from PySide6.QtGui import QGuiApplication, QPainter
from typing import List
from canvas.stroke import Stroke
from canvas.renderer import StrokeRenderer

class ScreenshotCapture:
    @staticmethod
    def capture_screen_with_annotations(
        file_path: str,
        strokes: List[Stroke],
        screen_index: int = 0,
        format_name: str = "PNG",
    ) -> bool:
        screens = QGuiApplication.screens()
        if not screens:
            return False
        target_screen = screens[screen_index] if 0 <= screen_index < len(screens) else screens[0]
        geo = target_screen.geometry()
        pixmap = target_screen.grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        image = pixmap.toImage()
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        StrokeRenderer.render_all(painter, strokes)
        painter.end()
        return image.save(file_path, format_name)
