import os
from PySide6.QtCore import QObject, QTimer, Signal
from typing import List, Callable
from canvas.stroke import Stroke
from persistence.project import ProjectPersistence
from app.config import ConfigManager

class AutosaveManager(QObject):
    autosave_completed = Signal(str)

    def __init__(self, get_strokes_callback: Callable[[], List[Stroke]], parent=None):
        super().__init__(parent)
        self.get_strokes_callback = get_strokes_callback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._perform_autosave)
        self.interval_minutes = 5
        self.enabled = True

    def configure(self, enabled: bool, interval_minutes: int):
        self.enabled = enabled
        self.interval_minutes = interval_minutes
        if self.timer.isActive():
            self.timer.stop()
        if enabled and interval_minutes > 0:
            self.timer.start(interval_minutes * 60 * 1000)

    def _perform_autosave(self):
        if not self.enabled:
            return
        strokes = self.get_strokes_callback()
        if not strokes:
            return
        autosave_dir = os.path.join(ConfigManager.get_config_dir(), "autosaves")
        os.makedirs(autosave_dir, exist_ok=True)
        autosave_file = os.path.join(autosave_dir, "autosave_current.whiteboard")
        if ProjectPersistence.save_project(autosave_file, strokes, 1920, 1080):
            self.autosave_completed.emit(autosave_file)
