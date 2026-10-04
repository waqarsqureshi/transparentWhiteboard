from PySide6.QtGui import QTabletEvent, QMouseEvent, QTouchEvent
from typing import Tuple

class InputHandler:
    @staticmethod
    def process_mouse_event(event: QMouseEvent) -> Tuple[float, float, float]:
        pos = event.position()
        return pos.x(), pos.y(), 1.0

    @staticmethod
    def process_tablet_event(event: QTabletEvent) -> Tuple[float, float, float]:
        pos = event.position()
        pressure = event.pressure()
        if pressure <= 0.0:
            pressure = 1.0
        return pos.x(), pos.y(), pressure

    @staticmethod
    def process_touch_point(touch_point) -> Tuple[float, float, float]:
        pos = touch_point.position()
        pressure = touch_point.pressure()
        if pressure <= 0.0 or pressure > 1.0:
            pressure = 1.0
        return pos.x(), pos.y(), pressure
