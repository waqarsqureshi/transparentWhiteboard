import uuid
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QMouseEvent, QTabletEvent, QTouchEvent, QPaintEvent
from PySide6.QtCore import Qt, Signal, QPointF
from typing import List, Optional
from canvas.stroke import Stroke
from canvas.renderer import StrokeRenderer
from canvas.input_handler import InputHandler
from commands.undo_redo_manager import UndoRedoManager, AddStrokeCommand, EraseStrokesCommand, ClearCanvasCommand
from app.constants import ToolType, EraserMode

class TransparentCanvas(QWidget):
    stroke_finished = Signal()
    canvas_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setMouseTracking(True)

        self.strokes: List[Stroke] = []
        self.current_stroke: Optional[Stroke] = None
        self.undo_manager = UndoRedoManager()

        self.current_tool: ToolType = ToolType.PEN
        self.current_colour: str = "#FF3B30"
        self.current_width: float = 4.0
        self.current_opacity: float = 1.0
        self.eraser_mode: EraserMode = EraserMode.STROKE
        self.eraser_radius: float = 20.0
        self.laser_pos: Optional[QPointF] = None
        self.bg_mode: str = "desktop"

    def set_bg_mode(self, mode: str):
        self.bg_mode = mode
        self.update()

    def set_tool(self, tool: ToolType):
        self.current_tool = tool
        if tool == ToolType.ERASER:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif tool == ToolType.LASER:
            self.setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_colour(self, colour: str):
        self.current_colour = colour

    def set_width(self, width: float):
        self.current_width = width

    def set_opacity(self, opacity: float):
        self.current_opacity = opacity

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            x, y, pressure = InputHandler.process_mouse_event(event)
            self._handle_pointer_down(x, y, pressure)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        x, y, pressure = InputHandler.process_mouse_event(event)
        self._handle_pointer_move(x, y, pressure)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_pointer_up()
            event.accept()

    def tabletEvent(self, event: QTabletEvent):
        x, y, pressure = InputHandler.process_tablet_event(event)
        if event.type() == QTabletEvent.Type.TabletPress:
            self._handle_pointer_down(x, y, pressure)
        elif event.type() == QTabletEvent.Type.TabletMove:
            self._handle_pointer_move(x, y, pressure)
        elif event.type() == QTabletEvent.Type.TabletRelease:
            self._handle_pointer_up()
        event.accept()

    def touchEvent(self, event: QTouchEvent):
        touch_points = event.points()
        if touch_points:
            pt = touch_points[0]
            x, y, pressure = InputHandler.process_touch_point(pt)
            if pt.state() == Qt.TouchPointState.TouchPointPressed:
                self._handle_pointer_down(x, y, pressure)
            elif pt.state() == Qt.TouchPointState.TouchPointMoved:
                self._handle_pointer_move(x, y, pressure)
            elif pt.state() == Qt.TouchPointState.TouchPointReleased:
                self._handle_pointer_up()
        event.accept()

    def _handle_pointer_down(self, x: float, y: float, pressure: float):
        if self.current_tool == ToolType.ERASER:
            self._erase_at(x, y)
        elif self.current_tool == ToolType.LASER:
            self.laser_pos = QPointF(x, y)
            self.update()
        else:
            self.current_stroke = Stroke(
                id=str(uuid.uuid4()),
                tool=self.current_tool.value,
                colour=self.current_colour,
                width=self.current_width,
                opacity=self.current_opacity,
            )
            self.current_stroke.add_point(x, y, pressure)
            self.update()

    def _handle_pointer_move(self, x: float, y: float, pressure: float):
        if self.current_tool == ToolType.ERASER:
            self._erase_at(x, y)
        elif self.current_tool == ToolType.LASER:
            self.laser_pos = QPointF(x, y)
            self.update()
        elif self.current_stroke is not None:
            self.current_stroke.add_point(x, y, pressure)
            self.update()

    def _handle_pointer_up(self):
        if self.current_tool == ToolType.LASER:
            self.laser_pos = None
            self.update()
        elif self.current_stroke is not None:
            if len(self.current_stroke.points) > 0:
                cmd = AddStrokeCommand(self.strokes, self.current_stroke)
                self.undo_manager.execute_command(cmd)
                self.stroke_finished.emit()
            self.current_stroke = None
            self.update()

    def _erase_at(self, x: float, y: float):
        removed = []
        for idx, stroke in enumerate(self.strokes):
            if stroke.intersects_point(x, y, tolerance=self.eraser_radius):
                removed.append((idx, stroke))
        if removed:
            cmd = EraseStrokesCommand(self.strokes, removed)
            self.undo_manager.execute_command(cmd)
            self.update()

    def undo(self) -> bool:
        success = self.undo_manager.undo()
        if success:
            self.update()
        return success

    def redo(self) -> bool:
        success = self.undo_manager.redo()
        if success:
            self.update()
        return success

    def clear(self):
        if self.strokes:
            cmd = ClearCanvasCommand(self.strokes)
            self.undo_manager.execute_command(cmd)
            self.canvas_cleared.emit()
            self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        if self.bg_mode == "dark":
            painter.fillRect(self.rect(), QColor(24, 24, 27))
        elif self.bg_mode == "white":
            painter.fillRect(self.rect(), QColor(252, 252, 252))
        elif self.bg_mode == "slides":
            painter.fillRect(self.rect(), QColor(15, 23, 42))
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self.bg_mode == "desktop":
            painter.setPen(QColor(59, 130, 246, 120))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        StrokeRenderer.render_all(painter, self.strokes)
        if self.current_stroke is not None:
            StrokeRenderer.render_stroke(painter, self.current_stroke)
        if self.laser_pos is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 59, 48, 200))
            painter.drawEllipse(self.laser_pos, 8, 8)
            painter.setBrush(QColor(255, 59, 48, 50))
            painter.drawEllipse(self.laser_pos, 18, 18)
        painter.end()
