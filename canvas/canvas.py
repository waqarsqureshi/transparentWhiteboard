import math
import time
import uuid
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QColor, QPen, QCursor, QPixmap,
    QMouseEvent, QTabletEvent, QTouchEvent, QPaintEvent,
)
from PySide6.QtCore import Qt, Signal, QPointF, QPoint, QRectF, QTimer
from typing import List, Optional, Tuple
from canvas.stroke import Stroke, Point
from canvas.renderer import StrokeRenderer
from canvas.input_handler import InputHandler
from commands.undo_redo_manager import (
    UndoRedoManager, AddStrokeCommand, EraseStrokesCommand,
    ClearCanvasCommand, UpdateStrokesCommand,
)
from app.constants import ToolType, EraserMode


class TransparentCanvas(QWidget):
    stroke_finished = Signal()
    canvas_cleared = Signal()
    history_changed = Signal(bool, bool)  # (can_undo, can_redo)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMouseTracking(True)

        self.strokes: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None
        self.undo_manager = UndoRedoManager()

        # Default tool on startup is Pen so the user can draw immediately
        self.current_tool: ToolType = ToolType.PEN
        self.current_colour: str = "#FF3B30"
        self.current_width: float = 4.0
        self.current_opacity: float = 1.0
        self.eraser_mode: EraserMode = EraserMode.POINT
        self.eraser_radius: float = 20.0
        self.eraser_pos: Optional[QPointF] = None
        self.bg_mode: str = "desktop"
        self.background_pixmap: Optional[QPixmap] = None

        # Pointer / rub state
        self._pointer_pressed: bool = False
        self._erase_before_snapshot: Optional[List[Stroke]] = None
        self._erased_during_drag: bool = False
        self._last_erase_pt: Optional[Tuple[float, float]] = None

        # Presentation laser pointer state + fading trail [(x, y, timestamp)]
        self.laser_pos: Optional[QPointF] = None
        self.laser_trail: List[Tuple[float, float, float]] = []
        self._laser_last_move: float = 0.0
        self._laser_timer = QTimer(self)
        self._laser_timer.setInterval(30)
        self._laser_timer.timeout.connect(self._tick_laser)

        # Floating windows (e.g. the toolbar) whose area must never be drawn on
        self.overlay_widgets: List[QWidget] = []
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _emit_history(self):
        self.history_changed.emit(self.undo_manager.can_undo(), self.undo_manager.can_redo())

    def _is_over_overlay(self, global_pt: QPoint) -> bool:
        """True if the point lies on a visible overlay (toolbar). Re-raises it so it
        regains its place above the canvas if the z-order was disturbed."""
        for w in self.overlay_widgets:
            if w is not None and w.isVisible() and w.frameGeometry().contains(global_pt):
                w.raise_()
                return True
        return False

    def set_bg_mode(self, mode: str):
        self.bg_mode = mode
        self.update()

    def set_background_pixmap(self, pixmap: Optional[QPixmap]):
        """Sets an optional background image/pixmap to display and export beneath strokes."""
        self.background_pixmap = pixmap
        self.update()

    def set_tool(self, tool: ToolType):
        if self._pointer_pressed:
            self._handle_pointer_up()
        self.current_tool = tool
        if tool != ToolType.ERASER:
            self.eraser_pos = None
        if tool != ToolType.LASER:
            self.laser_pos = None
            self.laser_trail.clear()
            self._laser_timer.stop()

        if tool == ToolType.ERASER:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif tool == ToolType.LASER:
            self.setCursor(Qt.CursorShape.BlankCursor)
            # Show laser dot immediately at current cursor position without requiring a click
            local_pt = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(local_pt):
                self.laser_pos = QPointF(local_pt.x(), local_pt.y())
        elif tool == ToolType.MOUSE:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def set_colour(self, colour: str):
        self.current_colour = colour

    def set_width(self, width: float):
        self.current_width = float(width)
        # Scale physical rubber size proportionally when user changes thickness
        self.eraser_radius = max(10.0, float(width) * 3.5)
        if self.current_tool == ToolType.ERASER:
            self.update()

    def set_eraser_radius(self, radius: float):
        self.eraser_radius = max(6.0, min(120.0, float(radius)))
        if self.current_tool == ToolType.ERASER:
            self.update()

    def set_opacity(self, opacity: float):
        self.current_opacity = opacity

    # --------------------------------------------------------- input events
    def mousePressEvent(self, event: QMouseEvent):
        if self.current_tool == ToolType.MOUSE:
            event.ignore()
            return
        if self._is_over_overlay(event.globalPosition().toPoint()):
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            x, y, pressure = InputHandler.process_mouse_event(event)
            self._handle_pointer_down(x, y, pressure)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.current_tool == ToolType.MOUSE:
            event.ignore()
            return
        x, y, pressure = InputHandler.process_mouse_event(event)
        # ONLY the Laser tool works without pressing the mouse button (until a new tool is selected)
        if self.current_tool == ToolType.LASER:
            if self._is_over_overlay(event.globalPosition().toPoint()):
                self.laser_pos = None
                self.update()
                event.ignore()
                return
            self._update_laser(x, y)
            event.accept()
            return

        # All other tools (Pen, Highlighter, Arrow, Line, Box, Eraser) require a button press
        if self._pointer_pressed:
            # Safely handle case where mouse button was released outside window
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                self._handle_pointer_up()
                event.accept()
                return
            self._handle_pointer_move(x, y, pressure)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.current_tool == ToolType.MOUSE:
            event.ignore()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_pointer_up()
            event.accept()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.current_tool == ToolType.ERASER:
            self.eraser_pos = None
            self.update()
        elif self.current_tool == ToolType.LASER:
            self.laser_pos = None
            self.laser_trail.clear()
            self.update()

    def tabletEvent(self, event: QTabletEvent):
        if self.current_tool == ToolType.MOUSE:
            event.ignore()
            return
        if (event.type() == QTabletEvent.Type.TabletPress
                and self._is_over_overlay(event.globalPosition().toPoint())):
            event.ignore()
            return
        x, y, pressure = InputHandler.process_tablet_event(event)
        if event.type() == QTabletEvent.Type.TabletPress:
            self._handle_pointer_down(x, y, pressure)
        elif event.type() == QTabletEvent.Type.TabletMove:
            if self.current_tool == ToolType.LASER or self._pointer_pressed:
                self._handle_pointer_move(x, y, pressure)
        elif event.type() == QTabletEvent.Type.TabletRelease:
            self._handle_pointer_up()
        event.accept()

    def touchEvent(self, event: QTouchEvent):
        if self.current_tool == ToolType.MOUSE:
            event.ignore()
            return
        touch_points = event.points()
        if touch_points:
            pt = touch_points[0]
            if (pt.state() == Qt.TouchPointState.TouchPointPressed
                    and self._is_over_overlay(pt.globalPosition().toPoint())):
                event.ignore()
                return
            x, y, pressure = InputHandler.process_touch_point(pt)
            if pt.state() == Qt.TouchPointState.TouchPointPressed:
                self._handle_pointer_down(x, y, pressure)
            elif pt.state() == Qt.TouchPointState.TouchPointMoved:
                self._handle_pointer_move(x, y, pressure)
            elif pt.state() == Qt.TouchPointState.TouchPointReleased:
                self._handle_pointer_up()
        event.accept()

    # ---------------------------------------------------- pointer handlers
    def _handle_pointer_down(self, x: float, y: float, pressure: float):
        if self.current_tool == ToolType.MOUSE:
            return
        self._pointer_pressed = True
        if self.current_tool == ToolType.ERASER:
            self.eraser_pos = QPointF(x, y)
            self._erase_before_snapshot = list(self.strokes)
            self._erased_during_drag = False
            self._last_erase_pt = (x, y)
            self._erase_at(x, y)
            self.update()
        elif self.current_tool == ToolType.LASER:
            self._update_laser(x, y)
        else:
            # Highlighter defaults to a broad marker width if standard thin pen width is active
            stroke_width = self.current_width
            if self.current_tool == ToolType.HIGHLIGHTER and stroke_width < 12.0:
                stroke_width = max(20.0, stroke_width * 4.5)
            self.current_stroke = Stroke(
                id=str(uuid.uuid4()),
                tool=self.current_tool.value,
                colour=self.current_colour,
                width=stroke_width,
                opacity=self.current_opacity,
            )
            self.current_stroke.add_point(x, y, pressure)
            self.update()

    def _handle_pointer_move(self, x: float, y: float, pressure: float):
        if self.current_tool == ToolType.MOUSE:
            return
        if self.current_tool == ToolType.ERASER:
            self.eraser_pos = QPointF(x, y)
            if not self._pointer_pressed:
                self.update()
                return
            # Sweep along path from last point so fast movements never skip over strokes
            if self._last_erase_pt is not None:
                lx, ly = self._last_erase_pt
                dist = math.hypot(x - lx, y - ly)
                step = max(2.0, self.eraser_radius * 0.4)
                if dist > step:
                    n_steps = int(math.ceil(dist / step))
                    for k in range(1, n_steps):
                        t = k / n_steps
                        self._erase_at(lx + t * (x - lx), ly + t * (y - ly))
            self._last_erase_pt = (x, y)
            self._erase_at(x, y)
            self.update()
        elif self.current_tool == ToolType.LASER:
            self._update_laser(x, y)
        elif self.current_stroke is not None:
            if self.current_tool in (ToolType.LINE, ToolType.ARROW, ToolType.RECTANGLE):
                if len(self.current_stroke.points) > 1:
                    self.current_stroke.points[1] = Point(x=x, y=y, pressure=pressure)
                else:
                    self.current_stroke.add_point(x, y, pressure)
            else:
                # Filter out duplicate zero-distance points to avoid spline kinks
                last_p = self.current_stroke.points[-1]
                if (x - last_p.x) ** 2 + (y - last_p.y) ** 2 >= 1.0:
                    self.current_stroke.add_point(x, y, pressure)
            self.update()

    def _handle_pointer_up(self):
        was_pressed = self._pointer_pressed
        self._pointer_pressed = False
        if self.current_tool == ToolType.MOUSE:
            return
        if self.current_tool == ToolType.ERASER:
            if was_pressed and self._erased_during_drag and self._erase_before_snapshot is not None:
                after_snapshot = list(self.strokes)
                cmd = UpdateStrokesCommand(self.strokes, self._erase_before_snapshot, after_snapshot)
                self.undo_manager.execute_command(cmd)
                self.stroke_finished.emit()
                self._emit_history()
            self._erase_before_snapshot = None
            self._erased_during_drag = False
            self._last_erase_pt = None
            self.eraser_pos = None
            self.update()
        elif self.current_tool == ToolType.LASER:
            self.update()
        elif self.current_stroke is not None:
            if self.current_tool in (ToolType.LINE, ToolType.ARROW, ToolType.RECTANGLE):
                if len(self.current_stroke.points) >= 2:
                    p0 = self.current_stroke.points[0]
                    p1 = self.current_stroke.points[1]
                    dist_sq = (p1.x - p0.x) ** 2 + (p1.y - p0.y) ** 2
                    if dist_sq >= 9.0:
                        cmd = AddStrokeCommand(self.strokes, self.current_stroke)
                        self.undo_manager.execute_command(cmd)
                        self.stroke_finished.emit()
                        self._emit_history()
            else:
                if len(self.current_stroke.points) > 0:
                    cmd = AddStrokeCommand(self.strokes, self.current_stroke)
                    self.undo_manager.execute_command(cmd)
                    self.stroke_finished.emit()
                    self._emit_history()
            self.current_stroke = None
            self.update()

    # ---------------------------------------------------- laser & erasing
    def _update_laser(self, x: float, y: float):
        now = time.time()
        self.laser_pos = QPointF(x, y)
        self._laser_last_move = now
        self.laser_trail.append((x, y, now))
        # Keep only recent trail points (last 280 ms)
        cutoff = now - 0.28
        self.laser_trail = [pt for pt in self.laser_trail if pt[2] >= cutoff]
        if not self._laser_timer.isActive():
            self._laser_timer.start()
        self.update()

    def _tick_laser(self):
        now = time.time()
        cutoff = now - 0.28
        self.laser_trail = [pt for pt in self.laser_trail if pt[2] >= cutoff]
        # Keep the laser dot visible while in Laser mode; stop timer once the motion trail finishes fading
        if not self.laser_trail:
            self._laser_timer.stop()
        self.update()

    def _erase_at(self, x: float, y: float):
        """
        Physical rubber partial erasing at (x, y) with radius self.eraser_radius.
        If self.eraser_mode == EraserMode.STROKE, removes whole intersecting strokes;
        otherwise (default EraserMode.POINT) partially erases only the rubbed section.
        """
        if not self.strokes:
            return
        if self.eraser_mode == EraserMode.STROKE:
            removed = []
            for idx, stroke in enumerate(self.strokes):
                if stroke.intersects_point(x, y, tolerance=self.eraser_radius):
                    removed.append((idx, stroke))
            if removed:
                if self._pointer_pressed:
                    for _, stroke in reversed(removed):
                        if stroke in self.strokes:
                            self.strokes.remove(stroke)
                    self._erased_during_drag = True
                else:
                    cmd = EraseStrokesCommand(self.strokes, removed)
                    self.undo_manager.execute_command(cmd)
                    self._emit_history()
                self.update()
            return

        # Partial physical rubber erasure
        before = list(self.strokes) if not self._pointer_pressed else None
        new_strokes: List[Stroke] = []
        changed = False
        for stroke in self.strokes:
            modified, pieces = stroke.erase_circle(x, y, self.eraser_radius)
            if modified:
                changed = True
                new_strokes.extend(pieces)
            else:
                new_strokes.append(stroke)

        if changed:
            self.strokes[:] = new_strokes
            if self._pointer_pressed:
                self._erased_during_drag = True
            elif before is not None:
                cmd = UpdateStrokesCommand(self.strokes, before, list(self.strokes))
                self.undo_manager.execute_command(cmd)
                self.stroke_finished.emit()
                self._emit_history()
            self.update()

    def undo(self) -> bool:
        success = self.undo_manager.undo()
        if success:
            self._emit_history()
            self.update()
        return success

    def redo(self) -> bool:
        success = self.undo_manager.redo()
        if success:
            self._emit_history()
            self.update()
        return success

    def clear(self):
        if self.strokes:
            cmd = ClearCanvasCommand(self.strokes)
            self.undo_manager.execute_command(cmd)
            self.canvas_cleared.emit()
            self._emit_history()
            self.update()

    def load_strokes(self, strokes: List[Stroke]):
        """Replaces canvas strokes with loaded project strokes (undoable)."""
        before = list(self.strokes)
        cmd = UpdateStrokesCommand(self.strokes, before, list(strokes))
        self.undo_manager.execute_command(cmd)
        self._emit_history()
        self.update()

    # ------------------------------------------------------------ painting
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        if self.bg_mode == "dark":
            painter.fillRect(self.rect(), QColor(24, 24, 27))
        elif self.bg_mode == "white":
            painter.fillRect(self.rect(), QColor(252, 252, 252))
        elif self.bg_mode == "slides":
            painter.fillRect(self.rect(), QColor(15, 23, 42))
        elif self.bg_mode and self.bg_mode.startswith("#") and QColor(self.bg_mode).isValid():
            painter.fillRect(self.rect(), QColor(self.bg_mode))
        else:
            # Practically invisible alpha=1 fill so Windows routes pointer events in Draw mode
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.background_pixmap is not None and not self.background_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.background_pixmap)

        StrokeRenderer.render_all(painter, self.strokes)
        if self.current_stroke is not None:
            StrokeRenderer.render_stroke(painter, self.current_stroke)

        # Circular physical rubber cursor
        if self.current_tool == ToolType.ERASER and self.eraser_pos is not None:
            r = self.eraser_radius
            painter.setBrush(QColor(255, 255, 255, 45))
            painter.setPen(QPen(QColor(15, 23, 42, 210), 2.0))
            painter.drawEllipse(self.eraser_pos, r, r)
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.0, Qt.PenStyle.DashLine))
            painter.drawEllipse(self.eraser_pos, max(1.0, r - 1.5), max(1.0, r - 1.5))

        # Presentation laser pointer + fading trail
        if self.current_tool == ToolType.LASER:
            now = time.time()
            if len(self.laser_trail) >= 2:
                for i in range(len(self.laser_trail) - 1):
                    x0, y0, t0 = self.laser_trail[i]
                    x1, y1, t1 = self.laser_trail[i + 1]
                    age = max(0.0, min(1.0, 1.0 - (now - t1) / 0.28))
                    if age > 0.02:
                        trail_pen = QPen(
                            QColor(255, 59, 48, int(190 * age)),
                            max(1.5, 7.0 * age),
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                        )
                        painter.setPen(trail_pen)
                        painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

            if self.laser_pos is not None:
                painter.setPen(Qt.PenStyle.NoPen)
                # Outer soft halo
                painter.setBrush(QColor(255, 59, 48, 55))
                painter.drawEllipse(self.laser_pos, 18, 18)
                # Mid glow
                painter.setBrush(QColor(255, 59, 48, 180))
                painter.drawEllipse(self.laser_pos, 9, 9)
                # Bright white-hot core
                painter.setBrush(QColor(255, 245, 245, 245))
                painter.drawEllipse(self.laser_pos, 4, 4)

        painter.end()
