from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QColorDialog, QLabel
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtCore import Qt, QPoint, Signal
from app.constants import ToolType, DEFAULT_COLORS

class ColorButton(QPushButton):
    color_selected = Signal(str)
    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_active = False
        self.clicked.connect(lambda: self.color_selected.emit(self.color_hex))
        self.update_style()
    def set_active(self, active: bool):
        self._is_active = active
        self.update_style()
    def update_style(self):
        border = "2px solid #38BDF8" if self._is_active else "1px solid rgba(255,255,255,0.3)"
        self.setStyleSheet(f"QPushButton {{ background-color: {self.color_hex}; border-radius: 11px; border: {border}; }} QPushButton:hover {{ border: 2px solid white; }}")

class FloatingToolbar(QFrame):
    tool_changed = Signal(ToolType)
    color_changed = Signal(str)
    width_changed = Signal(float)
    undo_requested = Signal()
    redo_requested = Signal()
    clear_requested = Signal()
    save_annotation_requested = Signal()
    save_screenshot_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._drag_pos = QPoint()
        self._setup_ui()
        self.setStyleSheet("""
            QFrame#FloatingToolbar {
                background-color: rgba(15, 23, 42, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: #F1F5F9;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 9px;
                border-radius: 6px;
                min-height: 26px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.2); }
            QPushButton[active="true"] { background-color: #2563EB; color: white; border-color: #3B82F6; font-weight: 600; }
        """)
        self.setObjectName("FloatingToolbar")

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 5, 8, 5)
        self.layout.setSpacing(5)

        drag_handle = QLabel("⋮⋮")
        drag_handle.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 14px; font-weight: bold; padding: 0 2px;")
        drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        self.layout.addWidget(drag_handle)

        self.btn_pen = QPushButton("✎ Pen")
        self.btn_pen.setProperty("active", True)
        self.btn_pen.clicked.connect(lambda: self._select_tool(ToolType.PEN, self.btn_pen))
        self.layout.addWidget(self.btn_pen)

        self.btn_highlighter = QPushButton("🖍 Highlight")
        self.btn_highlighter.clicked.connect(lambda: self._select_tool(ToolType.HIGHLIGHTER, self.btn_highlighter))
        self.layout.addWidget(self.btn_highlighter)

        self.btn_eraser = QPushButton("⌫ Eraser")
        self.btn_eraser.clicked.connect(lambda: self._select_tool(ToolType.ERASER, self.btn_eraser))
        self.layout.addWidget(self.btn_eraser)

        self.btn_laser = QPushButton("🔴 Laser")
        self.btn_laser.clicked.connect(lambda: self._select_tool(ToolType.LASER, self.btn_laser))
        self.layout.addWidget(self.btn_laser)

        self.color_buttons = []
        for c in DEFAULT_COLORS[:6]:
            btn = ColorButton(c)
            btn.color_selected.connect(self._select_color)
            self.layout.addWidget(btn)
            self.color_buttons.append(btn)

        self.btn_custom_color = QPushButton("🎨")
        self.btn_custom_color.setFixedSize(26, 26)
        self.btn_custom_color.setStyleSheet("font-size: 13px; padding: 0;")
        self.btn_custom_color.clicked.connect(self._open_color_picker)
        self.layout.addWidget(self.btn_custom_color)

        for w in [2, 4, 8, 16]:
            w_btn = QPushButton(f"{w}px")
            w_btn.setFixedSize(36, 26)
            w_btn.setStyleSheet("font-size: 11px; padding: 2px;")
            w_btn.clicked.connect(lambda checked=False, width=w: self.width_changed.emit(width))
            self.layout.addWidget(w_btn)

        self.btn_undo = QPushButton("↶")
        self.btn_undo.setFixedSize(28, 26)
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        self.layout.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷")
        self.btn_redo.setFixedSize(28, 26)
        self.btn_redo.clicked.connect(self.redo_requested.emit)
        self.layout.addWidget(self.btn_redo)

        self.btn_clear = QPushButton("🗑")
        self.btn_clear.setFixedSize(28, 26)
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        self.layout.addWidget(self.btn_clear)

        self.btn_save = QPushButton("💾 Save PNG")
        self.btn_save.clicked.connect(self.save_annotation_requested.emit)
        self.layout.addWidget(self.btn_save)

        self.btn_screenshot = QPushButton("📸 Screen")
        self.btn_screenshot.clicked.connect(self.save_screenshot_requested.emit)
        self.layout.addWidget(self.btn_screenshot)

        self.btn_close = QPushButton("✕ Exit")
        self.btn_close.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.2); color: #FCA5A5; font-weight: 600; border: 1px solid rgba(239, 68, 68, 0.4); padding: 4px 10px; min-height: 26px; border-radius: 6px; } QPushButton:hover { background-color: #DC2626; color: white; }")
        self.btn_close.clicked.connect(self.exit_requested.emit)
        self.layout.addWidget(self.btn_close)

    def _select_tool(self, tool: ToolType, button: QPushButton):
        for btn in [self.btn_pen, self.btn_highlighter, self.btn_eraser, self.btn_laser]:
            btn.setProperty("active", False)
            btn.setStyle(btn.style())
        button.setProperty("active", True)
        button.setStyle(button.style())
        self.tool_changed.emit(tool)

    def _select_color(self, hex_code: str):
        for btn in self.color_buttons:
            btn.set_active(btn.color_hex.lower() == hex_code.lower())
        self.color_changed.emit(hex_code)

    def _open_color_picker(self):
        color = QColorDialog.getColor(initial=QColor("#FF3B30"), parent=self)
        if color.isValid():
            self._select_color(color.name())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
