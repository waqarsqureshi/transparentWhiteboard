from enum import Enum

class ToolType(str, Enum):
    MOUSE = "mouse"
    PEN = "pen"
    HIGHLIGHTER = "highlighter"
    LINE = "line"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    ERASER = "eraser"
    LASER = "laser"

class EraserMode(str, Enum):
    STROKE = "stroke"
    POINT = "point"

class BackgroundMode(str, Enum):
    DESKTOP = "desktop"
    WHITE = "white"
    DARK = "dark"
    SLIDES = "slides"

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
APP_VERSION = "1.1.0"
PROJECT_FILE_EXTENSION = ".whiteboard"
DEFAULT_AUTOSAVE_MINUTES = 5
