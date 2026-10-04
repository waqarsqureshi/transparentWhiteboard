from enum import Enum

class ToolType(str, Enum):
    PEN = "pen"
    HIGHLIGHTER = "highlighter"
    ERASER = "eraser"
    LASER = "laser"

class EraserMode(str, Enum):
    STROKE = "stroke"
    POINT = "point"

DEFAULT_COLORS = [
    "#FF3B30",
    "#34C759",
    "#007AFF",
    "#FFCC00",
    "#AF52DE",
    "#FF9500",
    "#000000",
    "#FFFFFF",
]

DEFAULT_PEN_WIDTHS = [2, 4, 6, 10, 15, 25]
APP_VERSION = "1.0.0"
PROJECT_FILE_EXTENSION = ".whiteboard"
DEFAULT_AUTOSAVE_MINUTES = 5
