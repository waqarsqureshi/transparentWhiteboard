"""
Compact floating toolbar for the Transparent Whiteboard.

- Icon + clear label controls with high-contrast active states and descriptive tooltips.
- StylePopup: colour swatches, custom colour picker, stroke thickness, and physical eraser size.
- SavePopup: predictable save/export workflow (Save PNG with background, Quick-save to
  Pictures/TransparentWhiteboard, Export transparent PNG, Save/Open editable .whiteboard project).
- DisplayPopup: shows detected OS monitors with resolution/DPI, explains single-monitor status
  clearly, switches displays when multiple monitors exist, and switches board background modes.
- Horizontal (top) or Vertical (left-dock) orientation, plus Squeeze (collapsed) mode.
- HelpPopup ('?'): complete guide to tools, modes, saving, display modes, and shortcuts.
"""
from PySide6.QtWidgets import (
    QFrame, QBoxLayout, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QColorDialog, QLabel,
)
from PySide6.QtGui import QColor, QMouseEvent, QGuiApplication, QPainterPath, QRegion
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, Signal
from app.constants import ToolType, DEFAULT_COLORS, BackgroundMode

BTN_W, BTN_H = 34, 32
STROKE_WIDTHS = [2, 4, 8, 16]
ERASER_RADII = [12, 20, 34, 52]


class ColorButton(QPushButton):
    color_selected = Signal(str)

    def __init__(self, color_hex: str, parent=None, size: int = 24):
        super().__init__(parent)
        self.color_hex = color_hex
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Colour {color_hex}")
        self._is_active = False
        self.clicked.connect(lambda: self.color_selected.emit(self.color_hex))
        self.update_style()

    def set_active(self, active: bool):
        self._is_active = active
        self.update_style()

    def update_style(self):
        border = "2px solid #38BDF8" if self._is_active else "1px solid rgba(255,255,255,0.35)"
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self.color_hex}; border-radius: {self._size // 2}px;"
            f" border: {border}; padding: 0; min-height: 0; }}"
            f"QPushButton:hover {{ border: 2px solid white; }}"
        )


class StylePopup(QFrame):
    """Popup holding colour palette, stroke thickness, and physical eraser size."""
    color_selected = Signal(str)
    width_selected = Signal(float)
    eraser_radius_selected = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("StylePopup")
        self.setStyleSheet("""
            QFrame#StylePopup { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; }
            QLabel { color: #94A3B8; font-size: 11px; font-weight: 600; }
            QPushButton { background-color: rgba(255,255,255,0.07); color: #F1F5F9; border: 1px solid rgba(255,255,255,0.14);
                          border-radius: 5px; font-size: 11px; min-height: 24px; padding: 0 6px; }
            QPushButton:hover { background-color: rgba(255,255,255,0.18); }
            QPushButton[active="true"] { background-color: #2563EB; border-color: #60A5FA; color: white; font-weight: bold; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        lay.addWidget(QLabel("Colour"))
        grid = QGridLayout()
        grid.setSpacing(6)
        self.color_buttons = []
        for i, c in enumerate(DEFAULT_COLORS):
            b = ColorButton(c, size=24)
            b.color_selected.connect(self._on_color)
            grid.addWidget(b, i // 4, i % 4)
            self.color_buttons.append(b)
        lay.addLayout(grid)

        btn_custom = QPushButton("Custom colour…")
        btn_custom.clicked.connect(self._on_custom)
        lay.addWidget(btn_custom)

        lay.addWidget(QLabel("Stroke Thickness"))
        row = QHBoxLayout()
        row.setSpacing(4)
        self.width_buttons = {}
        for w in STROKE_WIDTHS:
            b = QPushButton(f"{w}px")
            b.setFixedWidth(38)
            b.clicked.connect(lambda _=False, width=w: self._on_width(width))
            row.addWidget(b)
            self.width_buttons[w] = b
        lay.addLayout(row)

        lay.addWidget(QLabel("Eraser Rubber Size"))
        er_row = QHBoxLayout()
        er_row.setSpacing(4)
        self.eraser_buttons = {}
        labels = {12: "S", 20: "M", 34: "L", 52: "XL"}
        for r in ERASER_RADII:
            b = QPushButton(f"{labels[r]} ({r})")
            b.setFixedWidth(44)
            b.clicked.connect(lambda _=False, rad=r: self._on_eraser_radius(rad))
            er_row.addWidget(b)
            self.eraser_buttons[r] = b
        lay.addLayout(er_row)

    def set_current(self, color: str, width: float, eraser_radius: float = 20.0):
        for b in self.color_buttons:
            b.set_active(b.color_hex.lower() == color.lower())
        for w, b in self.width_buttons.items():
            b.setProperty("active", abs(w - width) < 0.5)
            b.setStyle(b.style())
        closest_r = min(ERASER_RADII, key=lambda r: abs(r - eraser_radius))
        for r, b in self.eraser_buttons.items():
            b.setProperty("active", r == closest_r)
            b.setStyle(b.style())

    def _on_color(self, c: str):
        self.color_selected.emit(c)
        self.hide()

    def _on_custom(self):
        self.hide()
        color = QColorDialog.getColor(initial=QColor("#FF3B30"), parent=None)
        if color.isValid():
            self.color_selected.emit(color.name())

    def _on_width(self, w: float):
        self.width_selected.emit(float(w))
        self.hide()

    def _on_eraser_radius(self, r: float):
        self.eraser_radius_selected.emit(float(r))
        self.hide()


class SavePopup(QFrame):
    """Predictable Save & Export menu explaining where and how files are saved."""
    save_as_image_requested = Signal()
    quick_save_requested = Signal()
    export_transparent_requested = Signal()
    save_project_requested = Signal()
    open_project_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("SavePopup")
        self.setStyleSheet("""
            QFrame#SavePopup { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; }
            QLabel#PopupTitle { color: #FFFFFF; font-size: 12px; font-weight: bold; }
            QLabel#PopupSub { color: #94A3B8; font-size: 11px; }
            QPushButton { background-color: rgba(255,255,255,0.07); color: #F1F5F9; border: 1px solid rgba(255,255,255,0.14);
                          border-radius: 6px; font-size: 12px; padding: 6px 10px; text-align: left; }
            QPushButton:hover { background-color: #2563EB; border-color: #60A5FA; color: white; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(5)

        title = QLabel("Save & Export Whiteboard")
        title.setObjectName("PopupTitle")
        lay.addWidget(title)

        sub = QLabel("Choose a file location or save an editable project:")
        sub.setObjectName("PopupSub")
        lay.addWidget(sub)

        self.btn_save_as = QPushButton("🖼  Save Image (PNG / JPG) — Choose Location…   [Ctrl+S]")
        self.btn_save_as.setToolTip("Captures the background + drawings and opens a Save File dialog")
        self.btn_save_as.clicked.connect(lambda: (self.hide(), self.save_as_image_requested.emit()))
        lay.addWidget(self.btn_save_as)

        self.btn_quick = QPushButton("⚡  Quick-Save PNG to Pictures\\TransparentWhiteboard   [Ctrl+Shift+S]")
        self.btn_quick.setToolTip("Immediately saves a timestamped PNG into your Pictures\\TransparentWhiteboard folder")
        self.btn_quick.clicked.connect(lambda: (self.hide(), self.quick_save_requested.emit()))
        lay.addWidget(self.btn_quick)

        self.btn_transparent = QPushButton("🔲  Export Transparent PNG (Strokes Only)…")
        self.btn_transparent.setToolTip("Exports only your drawn annotations on a transparent PNG background")
        self.btn_transparent.clicked.connect(lambda: (self.hide(), self.export_transparent_requested.emit()))
        lay.addWidget(self.btn_transparent)

        self.btn_save_proj = QPushButton("📄  Save Editable Project (.whiteboard)…")
        self.btn_save_proj.setToolTip("Saves editable strokes, colours, highlighters, lines, and arrows to a .whiteboard file")
        self.btn_save_proj.clicked.connect(lambda: (self.hide(), self.save_project_requested.emit()))
        lay.addWidget(self.btn_save_proj)

        self.btn_open_proj = QPushButton("📂  Open Editable Project (.whiteboard)…   [Ctrl+O]")
        self.btn_open_proj.setToolTip("Loads a previously saved .whiteboard project file onto the canvas")
        self.btn_open_proj.clicked.connect(lambda: (self.hide(), self.open_project_requested.emit()))
        lay.addWidget(self.btn_open_proj)


class DisplayPopup(QFrame):
    """Display & Screen Mode selector showing detected monitors and board background options."""
    screen_selected = Signal(int)
    bg_mode_selected = Signal(str)
    refit_fullscreen_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("DisplayPopup")
        self.setStyleSheet("""
            QFrame#DisplayPopup { background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; }
            QLabel#SectionTitle { color: #FFFFFF; font-size: 12px; font-weight: bold; }
            QLabel#InfoNote { color: #94A3B8; font-size: 11px; }
            QPushButton { background-color: rgba(255,255,255,0.07); color: #F1F5F9; border: 1px solid rgba(255,255,255,0.14);
                          border-radius: 6px; font-size: 12px; padding: 5px 10px; text-align: left; }
            QPushButton:hover { background-color: rgba(255,255,255,0.18); }
            QPushButton[active="true"] { background-color: #2563EB; border-color: #60A5FA; color: white; font-weight: 600; }
        """)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 10, 10, 10)
        self.lay.setSpacing(5)

    def populate(self, active_screen_index: int, active_bg_mode: str):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lbl_disp = QLabel("Connected Displays (OS Monitor Selection)")
        lbl_disp.setObjectName("SectionTitle")
        self.lay.addWidget(lbl_disp)

        screens = QGuiApplication.screens()
        for idx, scr in enumerate(screens):
            geo = scr.geometry()
            dpr = scr.devicePixelRatio()
            phys_w = int(round(geo.width() * dpr))
            phys_h = int(round(geo.height() * dpr))
            scale_pct = int(round(dpr * 100))
            status = " (Active)" if idx == active_screen_index else ""
            btn = QPushButton(f"🖥  Display {idx + 1}: {phys_w}×{phys_h} px ({scale_pct}% scale){status}")
            btn.setProperty("active", idx == active_screen_index)
            btn.clicked.connect(lambda _=False, i=idx: (self.hide(), self.screen_selected.emit(i)))
            self.lay.addWidget(btn)

        if len(screens) == 1:
            note = QLabel(
                "Windows currently reports 1 connected physical display.\n"
                "Connect a second monitor or projector to move the whiteboard across screens."
            )
            note.setObjectName("InfoNote")
            note.setWordWrap(True)
            self.lay.addWidget(note)

        lbl_bg = QLabel("Screen / Board Mode (Preserves Drawings)")
        lbl_bg.setObjectName("SectionTitle")
        self.lay.addWidget(lbl_bg)

        modes = [
            (BackgroundMode.DESKTOP.value, "🔲  Transparent Desktop Overlay (Draw over Chrome / apps)"),
            (BackgroundMode.WHITE.value, "⬜  Whiteboard Mode (Solid White Teaching Board)"),
            (BackgroundMode.DARK.value, "⬛  Blackboard Mode (Solid Dark Lecture Board)"),
            (BackgroundMode.SLIDES.value, "🟦  Slate Board Mode (Dark Navy Presentation Board)"),
        ]
        for mode_val, label in modes:
            b = QPushButton(label)
            b.setProperty("active", active_bg_mode == mode_val)
            b.clicked.connect(lambda _=False, m=mode_val: (self.hide(), self.bg_mode_selected.emit(m)))
            self.lay.addWidget(b)

        btn_refit = QPushButton("⛶  Re-fit Full-Screen Canvas to Display   [F11]")
        btn_refit.clicked.connect(lambda: (self.hide(), self.refit_fullscreen_requested.emit()))
        self.lay.addWidget(btn_refit)


HELP_HTML = """
<div style='font-size:12px; color:#E2E8F0;'>
<p style='font-size:14px; font-weight:600; color:#FFFFFF; margin:0 0 6px 0;'>Transparent Whiteboard – Complete Guide</p>

<p style='color:#94A3B8; margin:6px 0 2px 0;'><b>1. DRAWING &amp; MOUSE MODES</b></p>
<table cellspacing='0' cellpadding='2'>
<tr><td>✎&nbsp;<b>Pen (Default)</b></td><td>Active on startup. Draw smooth continuous strokes immediately.</td></tr>
<tr><td>🖱&nbsp;<b>Mouse</b></td><td>Click-through mode: clicks, scrolling and typing go directly to Chrome / slides while drawings stay on screen.</td></tr>
<tr><td>🖍&nbsp;<b>Highlighter</b></td><td>Broad translucent marker that keeps underlying text and drawings visible.</td></tr>
<tr><td>➔&nbsp;<b>Arrow / ╱ Line / ▭ Box</b></td><td>Press and drag to preview; release to finish a straight arrow, line, or box.</td></tr>
<tr><td>⌫&nbsp;<b>Physical Eraser</b></td><td>Hold the mouse button and rub across any stroke, line, or arrow to erase the portion under the circular rubber.</td></tr>
<tr><td>◉&nbsp;<b>Laser Pointer</b></td><td>Bright presentation pointer with a smooth fading trail (leaves no permanent marks).</td></tr>
</table>

<p style='color:#94A3B8; margin:8px 0 2px 0;'><b>2. COLOUR, SAVING &amp; SCREEN MODES</b></p>
<table cellspacing='0' cellpadding='2'>
<tr><td>●&nbsp;<b>Style</b></td><td>Pick stroke colour, custom colour, line thickness, and physical eraser size.</td></tr>
<tr><td>▣&nbsp;<b>Board Mode</b></td><td>Cycle between Transparent Desktop Overlay, Solid Whiteboard, and Solid Blackboard without losing drawings.</td></tr>
<tr><td>↶ / ↷ / <b>Clear</b></td><td>Undo / Redo recent actions, or <b>Clear</b> the entire board (asks confirmation first).</td></tr>
<tr><td>💾&nbsp;<b>Save / Export</b></td><td>Save PNG/JPG with background (choose location), Quick-save to <i>Pictures\\TransparentWhiteboard</i>, export transparent PNG, or Save/Open editable <i>.whiteboard</i> project files.</td></tr>
<tr><td>🖥&nbsp;<b>Display</b></td><td>Select monitor (when multiple displays are connected), switch board mode, or re-fit full-screen canvas.</td></tr>
<tr><td>⇅ / ◀ / ⋮⋮</td><td>Switch horizontal vs. left vertical dock (⇅), Squeeze/collapse (◀), or drag handle (⋮⋮).</td></tr>
</table>

<p style='color:#94A3B8; margin:8px 0 2px 0;'><b>3. KEYBOARD SHORTCUTS</b></p>
<table cellspacing='0' cellpadding='2'>
<tr><td><b>F2</b> or <b>Ctrl+Alt+M</b></td><td>Switch Mouse ⇄ Draw (works anywhere, even inside Chrome)</td></tr>
<tr><td><b>Esc</b></td><td>Return to Mouse mode (while in Draw mode)</td></tr>
<tr><td><b>Ctrl+Z / Ctrl+Y</b></td><td>Undo / Redo</td></tr>
<tr><td><b>Delete</b></td><td>Clear Whiteboard (with confirmation)</td></tr>
<tr><td><b>Ctrl+S / Ctrl+Shift+S</b></td><td>Save Image As… / Quick-Save to Pictures\\TransparentWhiteboard</td></tr>
<tr><td><b>Ctrl+O</b></td><td>Open editable <i>.whiteboard</i> project</td></tr>
<tr><td><b>F11</b></td><td>Re-fit full-screen canvas to current display</td></tr>
<tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>
</table>
</div>
"""


class HelpPopup(QFrame):
    """'How to use' panel shown from the ? button. Closes on any outside click."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("HelpPopup")
        self.setStyleSheet("QFrame#HelpPopup { background-color: #0F172A; border: 1px solid #334155;"
                           " border-radius: 8px; } QLabel { color: #E2E8F0; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        label = QLabel(HELP_HTML)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        label.setFixedWidth(440)
        lay.addWidget(label)


class FloatingToolbar(QFrame):
    tool_changed = Signal(ToolType)
    color_changed = Signal(str)
    width_changed = Signal(float)
    eraser_radius_changed = Signal(float)
    undo_requested = Signal()
    redo_requested = Signal()
    clear_requested = Signal()
    bg_mode_changed = Signal(str)
    save_annotation_requested = Signal()
    save_screenshot_requested = Signal()
    quick_save_requested = Signal()
    export_transparent_requested = Signal()
    save_project_requested = Signal()
    open_project_requested = Signal()
    exit_requested = Signal()
    next_screen_requested = Signal()
    screen_index_requested = Signal(int)
    refit_fullscreen_requested = Signal()
    layout_changed = Signal()

    def __init__(self, parent=None, vertical: bool = False):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setObjectName("FloatingToolbar")

        self._drag_pos = None
        self.is_collapsed = False
        self.is_vertical = vertical
        self.current_bg_mode = BackgroundMode.DESKTOP.value
        self.current_color = DEFAULT_COLORS[0]
        self.current_width = 4.0
        self.current_eraser_radius = 20.0
        self.current_screen_index = 0

        self.style_popup = StylePopup(self)
        self.style_popup.color_selected.connect(self._select_color)
        self.style_popup.width_selected.connect(self._select_width)
        self.style_popup.eraser_radius_selected.connect(self._select_eraser_radius)

        self.save_popup = SavePopup(self)
        self.save_popup.save_as_image_requested.connect(self.save_screenshot_requested.emit)
        self.save_popup.quick_save_requested.connect(self.quick_save_requested.emit)
        self.save_popup.export_transparent_requested.connect(self.export_transparent_requested.emit)
        self.save_popup.save_project_requested.connect(self.save_project_requested.emit)
        self.save_popup.open_project_requested.connect(self.open_project_requested.emit)

        self.display_popup = DisplayPopup(self)
        self.display_popup.screen_selected.connect(self.screen_index_requested.emit)
        self.display_popup.bg_mode_selected.connect(self.set_bg_mode_value)
        self.display_popup.refit_fullscreen_requested.connect(self.refit_fullscreen_requested.emit)

        self._setup_ui()
        self._apply_styles()
        self._apply_orientation()

    # ------------------------------------------------------------------ UI
    def _apply_styles(self):
        self.setStyleSheet("""
            QFrame#FloatingToolbar {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QPushButton {
                background-color: transparent;
                color: #F1F5F9;
                font-size: 15px;
                padding: 0;
                border-radius: 6px;
                border: 1px solid transparent;
            }
            QPushButton:hover:enabled { background-color: rgba(255, 255, 255, 0.14); }
            QPushButton:disabled { color: rgba(241, 245, 249, 0.28); }
            QPushButton[active="true"] { background-color: #2563EB; border-color: #60A5FA; color: white; }
            QPushButton[mouseActive="true"] { background-color: #059669; border-color: #34D399; color: white; }
            QPushButton#ClearButton {
                font-size: 11px; font-weight: 600; color: #FCA5A5;
                border: 1px solid rgba(252, 165, 165, 0.3); padding: 0 5px;
            }
            QPushButton#ClearButton:hover:enabled { background-color: rgba(220, 38, 38, 0.35); color: white; }
            QPushButton#CloseButton { color: #FCA5A5; }
            QPushButton#CloseButton:hover { background-color: #DC2626; color: white; }
            QPushButton#HelpButton { color: #7DD3FC; font-weight: bold; font-size: 15px;
                                     border: 1px solid rgba(125, 211, 252, 0.45); border-radius: 15px; }
            QPushButton#HelpButton:hover { background-color: rgba(125, 211, 252, 0.2); }
            QFrame#Separator { background-color: rgba(255, 255, 255, 0.18); border: none; }
            QLabel#DragHandle { color: rgba(255,255,255,0.45); font-size: 13px; font-weight: bold; }
        """)

    def _btn(self, text: str, tip: str, slot=None, width: int = BTN_W) -> QPushButton:
        b = QPushButton(text)
        b.setFixedSize(width, BTN_H)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if slot is not None:
            b.clicked.connect(slot)
        self.layout.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)
        return b

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setObjectName("Separator")
        self._separators.append(s)
        self.layout.addWidget(s, 0, Qt.AlignmentFlag.AlignCenter)
        return s

    def _setup_ui(self):
        self._separators = []
        self.layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.layout.setContentsMargins(6, 5, 6, 5)
        self.layout.setSpacing(3)

        self.drag_handle = QLabel("⋮⋮")
        self.drag_handle.setObjectName("DragHandle")
        self.drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        self.drag_handle.setToolTip("Drag to move the toolbar")
        self.layout.addWidget(self.drag_handle, 0, Qt.AlignmentFlag.AlignCenter)

        # Tools (Pen is active by default on startup)
        self.btn_mouse = self._btn("🖱", "Mouse – click through to Chrome / slides  [F2 or Ctrl+Alt+M]",
                                   lambda: self._select_tool(ToolType.MOUSE, self.btn_mouse))
        self.btn_pen = self._btn("✎", "Pen (Default) – draw smooth continuous strokes  [F2 toggles Mouse/Draw]",
                                 lambda: self._select_tool(ToolType.PEN, self.btn_pen))
        self.btn_pen.setProperty("active", True)
        self.btn_highlighter = self._btn("🖍", "Highlighter – translucent broad marker",
                                         lambda: self._select_tool(ToolType.HIGHLIGHTER, self.btn_highlighter))
        self.btn_arrow = self._btn("➔", "Arrow – drag from start to endpoint",
                                   lambda: self._select_tool(ToolType.ARROW, self.btn_arrow))
        self.btn_rect = self._btn("▭", "Rectangle – drag to draw box",
                                  lambda: self._select_tool(ToolType.RECTANGLE, self.btn_rect))
        self.btn_line = self._btn("╱", "Straight Line – drag from start to endpoint",
                                  lambda: self._select_tool(ToolType.LINE, self.btn_line))
        self.btn_eraser = self._btn("⌫", "Physical Rubber Eraser – hold and rub across strokes to erase partially",
                                    lambda: self._select_tool(ToolType.ERASER, self.btn_eraser))
        self.btn_laser = self._btn("◉", "Laser Pointer – visible pointer with fading trail (no permanent marks)",
                                   lambda: self._select_tool(ToolType.LASER, self.btn_laser))
        sep_a = self._sep()

        # Style (colour + thickness + eraser rubber size popup)
        self.btn_style = self._btn("●", "Colour, stroke thickness & eraser rubber size", self._open_style_popup)
        self._update_style_button()
        sep_b = self._sep()

        # Board mode + Undo / Redo + distinct Clear Whiteboard + Save
        self.btn_bg = self._btn("▣", "Board Mode: Transparent Desktop (click to cycle Transparent → Whiteboard → Blackboard)",
                                self._toggle_bg_mode)
        self.btn_undo = self._btn("↶", "Undo last operation  [Ctrl+Z]", self.undo_requested.emit)
        self.btn_redo = self._btn("↷", "Redo  [Ctrl+Y]", self.redo_requested.emit)
        self.btn_undo.setEnabled(False)
        self.btn_redo.setEnabled(False)

        self.btn_clear = self._btn("Clear", "Clear Whiteboard – delete all drawings (asks confirmation)  [Delete]",
                                   self.clear_requested.emit, width=42)
        self.btn_clear.setObjectName("ClearButton")

        self.btn_save = self._btn("💾", "Save & Export Whiteboard (PNG with background, Quick-Save, or .whiteboard project)  [Ctrl+S]",
                                  self._open_save_popup)
        sep_c = self._sep()

        # Display / orientation / squeeze / help / exit
        self.btn_screen = self._btn("🖥", "Displays & Screen Mode (select monitor, board background, or re-fit full-screen)",
                                    self._open_display_popup)
        self.btn_orient = self._btn("⇅", "Switch toolbar position: top horizontal bar ⇄ left vertical dock",
                                    self.toggle_orientation)
        self.btn_collapse = self._btn("◀", "Squeeze Mode – collapse / expand toolbar", self.toggle_collapse)
        self.btn_help = self._btn("?", "How to use & keyboard shortcuts", self.show_help)
        self.btn_help.setObjectName("HelpButton")
        self.btn_close = self._btn("✕", "Exit Whiteboard  [Ctrl+Q]", self.exit_requested.emit)
        self.btn_close.setObjectName("CloseButton")

        self._tool_buttons = {
            ToolType.MOUSE: self.btn_mouse,
            ToolType.PEN: self.btn_pen,
            ToolType.HIGHLIGHTER: self.btn_highlighter,
            ToolType.ARROW: self.btn_arrow,
            ToolType.RECTANGLE: self.btn_rect,
            ToolType.LINE: self.btn_line,
            ToolType.ERASER: self.btn_eraser,
            ToolType.LASER: self.btn_laser,
        }
        # Hidden when collapsed in Squeeze Mode (Mouse, Pen, Help, Expand and Close stay visible)
        self._collapsible = [
            self.btn_highlighter, self.btn_arrow, self.btn_rect, self.btn_line,
            self.btn_eraser, self.btn_laser, sep_a, self.btn_style, sep_b,
            self.btn_bg, self.btn_undo, self.btn_redo, self.btn_clear, self.btn_save,
            sep_c, self.btn_screen, self.btn_orient,
        ]

    def set_history_state(self, can_undo: bool, can_redo: bool):
        self.btn_undo.setEnabled(bool(can_undo))
        self.btn_redo.setEnabled(bool(can_redo))

    def _apply_orientation(self):
        if self.is_vertical:
            self.layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self.drag_handle.setText("⋯")
            self.btn_clear.setFixedSize(BTN_W, BTN_H)
            self.btn_clear.setText("Clr")
            for s in self._separators:
                s.setFixedSize(22, 1)
        else:
            self.layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self.drag_handle.setText("⋮⋮")
            self.btn_clear.setFixedSize(42, BTN_H)
            self.btn_clear.setText("Clear")
            for s in self._separators:
                s.setFixedSize(1, 22)
        self._update_collapse_glyph()
        self._relayout()

    def _update_collapse_glyph(self):
        if self.is_vertical:
            self.btn_collapse.setText("▼" if self.is_collapsed else "▲")
        else:
            self.btn_collapse.setText("▶" if self.is_collapsed else "◀")

    def _relayout(self):
        self.layout.invalidate()
        self.layout.activate()
        self.adjustSize()
        self.resize(self.sizeHint())
        self.layout_changed.emit()

    # ------------------------------------------------------------ actions
    def _select_tool(self, tool: ToolType, button: QPushButton, emit: bool = True):
        for btn in self._tool_buttons.values():
            btn.setProperty("active", False)
            btn.setProperty("mouseActive", False)
            btn.setStyle(btn.style())
        if tool == ToolType.MOUSE:
            button.setProperty("mouseActive", True)
        else:
            button.setProperty("active", True)
        button.setStyle(button.style())
        if emit:
            self.tool_changed.emit(tool)

    def set_active_tool(self, tool: ToolType):
        """Update the highlighted button only (does NOT emit tool_changed)."""
        if tool in self._tool_buttons:
            self._select_tool(tool, self._tool_buttons[tool], emit=False)

    def _update_style_button(self):
        self.btn_style.setStyleSheet(
            f"QPushButton {{ color: {self.current_color}; font-size: {10 + int(min(self.current_width, 16) * 0.6)}px; }}"
        )
        self.btn_style.setToolTip(
            f"Colour & thickness ({self.current_color}, {int(self.current_width)}px, eraser {int(self.current_eraser_radius)}px)"
        )

    def _open_style_popup(self):
        self._show_popup_near(
            self.style_popup,
            self.btn_style,
            lambda: self.style_popup.set_current(self.current_color, self.current_width, self.current_eraser_radius),
        )

    def _open_save_popup(self):
        # Automatically switch control to Mouse mode when Save is clicked so the user
        # has normal mouse and keyboard input without needing to press Esc first.
        self._select_tool(ToolType.MOUSE, self.btn_mouse)
        self._show_popup_near(self.save_popup, self.btn_save)

    def _open_display_popup(self):
        self._show_popup_near(
            self.display_popup,
            self.btn_screen,
            lambda: self.display_popup.populate(self.current_screen_index, self.current_bg_mode),
        )

    def show_help(self):
        if not hasattr(self, "help_popup"):
            self.help_popup = HelpPopup(self)
        self._show_popup_near(self.help_popup, self.btn_help)

    def _show_popup_near(self, popup: QFrame, anchor: QPushButton, prepare=None):
        if prepare:
            prepare()
        popup.adjustSize()
        g = anchor.mapToGlobal(QPoint(0, 0))
        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        size = popup.sizeHint()
        if self.is_vertical:
            pos = QPoint(g.x() + anchor.width() + 8, g.y())
            if pos.x() + size.width() > avail.right():
                pos.setX(self.x() - size.width() - 8)
        else:
            pos = QPoint(g.x(), g.y() + anchor.height() + 8)
            if pos.y() + size.height() > avail.bottom():
                pos.setY(self.y() - size.height() - 8)
        pos.setX(max(avail.left(), min(pos.x(), avail.right() - size.width())))
        pos.setY(max(avail.top(), min(pos.y(), avail.bottom() - size.height())))
        popup.move(pos)
        popup.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _select_color(self, hex_code: str):
        self.current_color = hex_code
        self._update_style_button()
        self.color_changed.emit(hex_code)

    def _select_width(self, width: float):
        self.current_width = float(width)
        self.current_eraser_radius = max(10.0, float(width) * 3.5)
        self._update_style_button()
        self.width_changed.emit(float(width))

    def _select_eraser_radius(self, radius: float):
        self.current_eraser_radius = float(radius)
        self._update_style_button()
        self.eraser_radius_changed.emit(float(radius))

    def set_bg_mode_value(self, mode: str):
        labels = {
            BackgroundMode.DESKTOP.value: "Transparent Desktop",
            BackgroundMode.WHITE.value: "Whiteboard (White)",
            BackgroundMode.DARK.value: "Blackboard (Dark)",
            BackgroundMode.SLIDES.value: "Slate Board (Navy)",
        }
        self.current_bg_mode = mode
        label = labels.get(mode, mode)
        self.btn_bg.setToolTip(f"Board Mode: {label} (click to cycle Transparent → Whiteboard → Blackboard)")
        self.bg_mode_changed.emit(self.current_bg_mode)

    def _toggle_bg_mode(self):
        cycle = {
            BackgroundMode.DESKTOP.value: BackgroundMode.WHITE.value,
            BackgroundMode.WHITE.value: BackgroundMode.DARK.value,
            BackgroundMode.DARK.value: BackgroundMode.DESKTOP.value,
        }
        next_mode = cycle.get(self.current_bg_mode, BackgroundMode.DESKTOP.value)
        self.set_bg_mode_value(next_mode)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        for w in self._collapsible:
            w.setVisible(not self.is_collapsed)
        self._update_collapse_glyph()
        self._relayout()

    def toggle_orientation(self):
        self.is_vertical = not self.is_vertical
        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        self._apply_orientation()
        if avail is not None:
            # Dock neatly to the left edge when switching to vertical, or top when horizontal
            if self.is_vertical:
                self.move(avail.left() + 12, max(avail.top() + 40, min(self.y(), avail.bottom() - self.height() - 12)))
            else:
                self.move(max(avail.left() + 40, min(self.x(), avail.right() - self.width() - 12)), avail.top() + 16)
            self.fit_to_screen(avail)

    # -------------------------------------------------------- positioning
    def fit_to_screen(self, avail: QRect = None):
        """Keep the toolbar fully visible; switch layout if it cannot fit."""
        if avail is None:
            screen = self.screen() or QGuiApplication.primaryScreen()
            avail = screen.availableGeometry()
        margin = 8
        if not self.is_vertical and self.width() > avail.width() - 2 * margin:
            self.is_vertical = True
            self._apply_orientation()
        if self.is_vertical and self.height() > avail.height() - 2 * margin and not self.is_collapsed:
            self.toggle_collapse()
        x = min(max(self.x(), avail.left() + margin), avail.right() - self.width() - margin + 1)
        y = min(max(self.y(), avail.top() + margin), avail.bottom() - self.height() - margin + 1)
        self.move(max(avail.left(), x), max(avail.top(), y))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_pos is not None:
            self._drag_pos = None
            self.fit_to_screen()
            event.accept()
