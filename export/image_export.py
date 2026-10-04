from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import Qt, QSize
from typing import List
from canvas.stroke import Stroke
from canvas.renderer import StrokeRenderer

class ImageExporter:
    @staticmethod
    def export_annotations_to_file(
        file_path: str,
        strokes: List[Stroke],
        width: int,
        height: int,
        format_name: str = "PNG",
        transparent: bool = True,
    ) -> bool:
        img_format = QImage.Format.Format_ARGB32_Premultiplied
        image = QImage(QSize(width, height), img_format)
        if transparent and format_name.upper() == "PNG":
            image.fill(Qt.GlobalColor.transparent)
        else:
            image.fill(QColor(255, 255, 255, 255))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        StrokeRenderer.render_all(painter, strokes)
        painter.end()
        return image.save(file_path, format_name)
