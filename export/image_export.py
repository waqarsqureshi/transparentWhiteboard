from PySide6.QtGui import QImage, QPainter, QColor, QPixmap
from PySide6.QtCore import Qt, QSize, QRect
from typing import List, Optional
from canvas.stroke import Stroke
from canvas.renderer import StrokeRenderer
from export.screenshot import BOARD_BG_COLOURS, ScreenshotCapture


class ImageExporter:
    @staticmethod
    def export_annotations_to_file(
        file_path: str,
        strokes: List[Stroke],
        width: int,
        height: int,
        format_name: str = "PNG",
        transparent: bool = False,
        bg_mode: str = "white",
        background_pixmap: Optional[QPixmap] = None,
        screen_index: int = 0,
        dpr: float = 1.0,
    ) -> bool:
        """
        Exports the whiteboard to an image file.
        When transparent=False (default), renders the background (board colour, background
        pixmap, or captured desktop screen) at the bottom and composites all strokes above it.
        When transparent=True, exports only the strokes on a transparent alpha channel.
        """
        if not transparent:
            return ScreenshotCapture.capture_screen_with_annotations(
                file_path=file_path,
                strokes=strokes,
                screen_index=screen_index,
                format_name=format_name,
                bg_mode=bg_mode,
                background_pixmap=background_pixmap,
                width=width,
                height=height,
                dpr=dpr,
            )

        scale = max(1.0, float(dpr))
        phys_w = max(1, int(round(width * scale)))
        phys_h = max(1, int(round(height * scale)))
        img_format = QImage.Format.Format_ARGB32_Premultiplied
        image = QImage(QSize(phys_w, phys_h), img_format)
        image.setDevicePixelRatio(scale)

        if format_name.upper() == "PNG":
            image.fill(Qt.GlobalColor.transparent)
        else:
            fill_col = BOARD_BG_COLOURS.get(bg_mode, QColor(252, 252, 252))
            image.fill(fill_col)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if background_pixmap is not None and not background_pixmap.isNull() and not transparent:
            painter.drawPixmap(QRect(0, 0, width, height), background_pixmap)
        StrokeRenderer.render_all(painter, strokes)
        painter.end()
        return image.save(file_path, format_name)
