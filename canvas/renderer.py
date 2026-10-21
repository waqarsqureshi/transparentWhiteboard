import math
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF
from typing import List
from canvas.stroke import Stroke


class StrokeRenderer:
    @staticmethod
    def _build_smooth_path(points) -> QPainterPath:
        """Builds a single continuous quadratic-Bezier QPainterPath through points."""
        path = QPainterPath()
        n = len(points)
        if n == 0:
            return path
        path.moveTo(points[0].x, points[0].y)
        if n == 1:
            return path
        if n == 2:
            path.lineTo(points[1].x, points[1].y)
            return path

        # First segment to midpoint between p0 and p1
        mid_x = (points[0].x + points[1].x) * 0.5
        mid_y = (points[0].y + points[1].y) * 0.5
        path.lineTo(mid_x, mid_y)

        # Smooth quadratic curves through intermediate points
        for i in range(1, n - 1):
            p_curr = points[i]
            p_next = points[i + 1]
            mid_nx = (p_curr.x + p_next.x) * 0.5
            mid_ny = (p_curr.y + p_next.y) * 0.5
            path.quadTo(p_curr.x, p_curr.y, mid_nx, mid_ny)

        # Final segment to last point
        path.lineTo(points[-1].x, points[-1].y)
        return path

    @staticmethod
    def render_stroke(painter: QPainter, stroke: Stroke):
        if not stroke.points:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        is_highlighter = stroke.tool == "highlighter"
        color = QColor(stroke.colour)
        if is_highlighter:
            # Translucent highlighter alpha (~35%) so underlying text & strokes stay visible
            hl_alpha = stroke.opacity * 0.35 if stroke.opacity >= 0.8 else stroke.opacity
            color.setAlpha(max(40, min(140, int(hl_alpha * 255))))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            # Highlighter uses a broad marker width
            draw_width = max(18.0, stroke.width * 3.0) if stroke.width < 12.0 else stroke.width
        else:
            color.setAlpha(max(1, min(255, int(stroke.opacity * 255))))
            draw_width = max(1.0, stroke.width)

        points = stroke.points
        n = len(points)

        # 1. Straight Line Tool
        if stroke.tool == "line" and n >= 2:
            p0 = points[0]
            p1 = points[-1]
            pen = QPen(color, draw_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(QPointF(p0.x, p0.y), QPointF(p1.x, p1.y))
            painter.restore()
            return

        # 2. Arrow Tool
        elif stroke.tool == "arrow" and n >= 2:
            p0 = points[0]
            p1 = points[-1]
            dx = p1.x - p0.x
            dy = p1.y - p0.y
            dist = math.hypot(dx, dy)
            pen = QPen(color, draw_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            if dist > 2:
                theta = math.atan2(dy, dx)
                head_len = max(14.0, min(40.0, draw_width * 3.8))
                arrow_angle = math.pi / 6.0  # 30 degrees

                # Stop shaft slightly inside arrowhead so thick lines don't poke past the tip
                shaft_end_x = p1.x - (head_len * 0.55) * math.cos(theta)
                shaft_end_y = p1.y - (head_len * 0.55) * math.sin(theta)
                if dist > head_len * 0.7:
                    painter.drawLine(QPointF(p0.x, p0.y), QPointF(shaft_end_x, shaft_end_y))
                else:
                    painter.drawLine(QPointF(p0.x, p0.y), QPointF(p1.x, p1.y))

                left_x = p1.x - head_len * math.cos(theta - arrow_angle)
                left_y = p1.y - head_len * math.sin(theta - arrow_angle)
                right_x = p1.x - head_len * math.cos(theta + arrow_angle)
                right_y = p1.y - head_len * math.sin(theta + arrow_angle)

                arrow_head = QPolygonF([
                    QPointF(p1.x, p1.y),
                    QPointF(left_x, left_y),
                    QPointF(right_x, right_y),
                ])
                painter.setPen(QPen(color, max(1.0, draw_width * 0.4), Qt.PenStyle.SolidLine,
                                    Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(QBrush(color))
                painter.drawPolygon(arrow_head)
            else:
                painter.drawLine(QPointF(p0.x, p0.y), QPointF(p1.x, p1.y))
            painter.restore()
            return

        # 3. Rectangle Tool
        elif stroke.tool == "rectangle" and n >= 2:
            p0 = points[0]
            p1 = points[-1]
            rx = min(p0.x, p1.x)
            ry = min(p0.y, p1.y)
            rw = abs(p1.x - p0.x)
            rh = abs(p1.y - p0.y)
            pen = QPen(color, draw_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(rx, ry, rw, rh), 4.0, 4.0)
            painter.restore()
            return

        # 4. Single Point Dot
        if n == 1:
            p = points[0]
            radius = max(1.0, (draw_width * p.pressure) / 2.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(p.x, p.y), radius, radius)
            painter.restore()
            return

        # 5. Highlighter: MUST draw as a single continuous path so segments never overdraw
        # and darken each other.
        if is_highlighter:
            full_path = StrokeRenderer._build_smooth_path(points)
            pen = QPen(color, draw_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(full_path)
            painter.restore()
            return

        # 6. Freehand Pen Stroke: if pressure is uniform (mouse/touch), draw as a single
        # smooth path for maximum sharpness and zero joint artifacts; if stylus pressure
        # varies, render per-segment with pressure modulation.
        pressures = [p.pressure for p in points]
        if max(pressures) - min(pressures) < 0.05:
            full_path = StrokeRenderer._build_smooth_path(points)
            avg_p = pressures[0]
            pen = QPen(color, max(1.0, draw_width * avg_p), Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(full_path)
            painter.restore()
            return

        for i in range(n - 1):
            p0 = points[i]
            p1 = points[i + 1]
            avg_pressure = (p0.pressure + p1.pressure) / 2.0
            current_width = max(1.0, draw_width * avg_pressure)

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
