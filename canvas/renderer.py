from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtCore import Qt, QPointF
from typing import List
from canvas.stroke import Stroke

class StrokeRenderer:
    @staticmethod
    def render_stroke(painter: QPainter, stroke: Stroke):
        if not stroke.points:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor(stroke.colour)
        alpha = int(stroke.opacity * 255)
        color.setAlpha(alpha)

        if stroke.tool == "highlighter":
            color.setAlpha(int(stroke.opacity * 0.4 * 255))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        points = stroke.points
        n = len(points)
        if n == 1:
            p = points[0]
            radius = (stroke.width * p.pressure) / 2.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
            painter.restore()
            return

        for i in range(n - 1):
            p0 = points[i]
            p1 = points[i + 1]
            avg_pressure = (p0.pressure + p1.pressure) / 2.0
            current_width = max(1.0, stroke.width * avg_pressure)

            pen = QPen(color, current_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            if i == 0:
                mid_x = (p0.x + p1.x) / 2.0
                mid_y = (p0.y + p1.y) / 2.0
                painter.drawLine(QPointF(p0.x, p0.y), QPointF(mid_x, mid_y))
            else:
                prev_p = points[i - 1]
                mid_prev_x = (prev_p.x + p0.x) / 2.0
                mid_prev_y = (prev_p.y + p0.y) / 2.0
                mid_curr_x = (p0.x + p1.x) / 2.0
                mid_curr_y = (p0.y + p1.y) / 2.0

                path = QPainterPath()
                path.moveTo(mid_prev_x, mid_prev_y)
                path.quadTo(p0.x, p0.y, mid_curr_x, mid_curr_y)
                painter.drawPath(path)

            if i == n - 2:
                mid_x = (p0.x + p1.x) / 2.0
                mid_y = (p0.y + p1.y) / 2.0
                painter.drawLine(QPointF(mid_x, mid_y), QPointF(p1.x, p1.y))

        painter.restore()

    @staticmethod
    def render_all(painter: QPainter, strokes: List[Stroke]):
        for stroke in strokes:
            StrokeRenderer.render_stroke(painter, stroke)
