"""
Fullscreen transparent annotation window.

Presenter-mode & Full-Screen Lecture Design:
  * Fills 100% of the active display viewport in both logical and physical (High-DPI)
    coordinates, automatically adapting to resolution and monitor changes.
  * Opens directly in Pen drawing mode so the user can draw immediately.
  * The canvas and toolbar are TOPMOST and never steal keyboard focus (WS_EX_NOACTIVATE),
    so Chrome, Google Slides, or PowerPoint keep focus for slide clickers and arrow keys.
  * Supports physical-rubber partial erasing, translucent highlighting, straight arrows
    and lines, a fading-trail presentation laser pointer, predictable saving/exporting
    (PNG with background, quick-save, transparent PNG, and editable .whiteboard projects),
    and clear display/screen-mode management.
"""
import os
import sys
import time
from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel, QMessageBox, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication

from canvas.canvas import TransparentCanvas
from ui.toolbar import FloatingToolbar
from app.config import WhiteboardConfig, ConfigManager
from export.image_export import ImageExporter
from export.screenshot import ScreenshotCapture
from persistence.autosave import AutosaveManager
from persistence.project import ProjectPersistence
from app.constants import ToolType

IS_WIN = sys.platform == "win32"
if IS_WIN:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_NOACTIVATE = 0x08000000
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
    SWP_FRAMECHANGED, SWP_SHOWWINDOW = 0x0020, 0x0040
    WM_HOTKEY = 0x0312
    MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x4000
    VK_F2, VK_F11, VK_ESCAPE, VK_DELETE = 0x71, 0x7A, 0x1B, 0x2E
    VK_M, VK_O, VK_Q, VK_S, VK_Y, VK_Z = 0x4D, 0x4F, 0x51, 0x53, 0x59, 0x5A
    WDA_NONE, WDA_EXCLUDEFROMCAPTURE = 0x00000000, 0x00000011
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL


def _set_exclude_from_capture(widget, exclude: bool = True) -> bool:
    """Uses Win32 WDA_EXCLUDEFROMCAPTURE so DWM omits the widget from screen grabs
    without hiding or flickering it on the physical display."""
    if not IS_WIN or widget is None:
        return False
    try:
        hwnd = wintypes.HWND(int(widget.winId()))
        flag = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
        return bool(user32.SetWindowDisplayAffinity(hwnd, flag))
    except Exception:
        return False


def _set_ex_style(widget, add: int = 0, remove: int = 0):
    if not IS_WIN:
        return
    hwnd = wintypes.HWND(int(widget.winId()))
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ctypes.c_long((style | add) & ~remove).value)


def _make_topmost(widget):
    """Move window to the top of the TOPMOST band without activating it."""
    if IS_WIN and widget.isVisible():
        user32.SetWindowPos(wintypes.HWND(int(widget.winId())), wintypes.HWND(HWND_TOPMOST),
                            0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


class TransparentWhiteboardWindow(QMainWindow):
    # Global hotkey ids
    HK_TOGGLE_F2 = 101
    HK_TOGGLE_CAM = 102
    HK_ESC = 110
    HK_UNDO = 111
    HK_REDO = 112
    HK_CLEAR = 113
    HK_SAVE = 114
    HK_QUICK_SAVE = 115
    HK_QUIT = 116
    HK_OPEN = 117
    HK_REFIT = 118

    def __init__(self, screen_index: int = 0, config: WhiteboardConfig = None):
        super().__init__()
        self.screen_index = screen_index
        self.config = config or ConfigManager.load()
        self.is_mouse_mode = False
        self.has_unsaved_changes = False
        self.prompt_unsaved_on_close = False
        self._registered_hotkeys = set()
        self._connected_screens = set()

        # Frameless, always on top, translucent, and never steals focus from Chrome
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setContentsMargins(0, 0, 0, 0)

        # Fullscreen transparent canvas (Pen mode active immediately on startup)
        self.canvas = TransparentCanvas(self)
        self.canvas.set_bg_mode("desktop")
        self.canvas.set_colour(self.config.default_color)
        self.canvas.set_width(self.config.default_width)
        self.canvas.set_tool(ToolType.PEN)
        self.setCentralWidget(self.canvas)

        # Toast for non-intrusive notifications
        self.toast = QLabel(self.canvas)
        self.toast.setStyleSheet(
            "QLabel { background-color: rgba(15,23,42,0.94); color: #F1F5F9; font-size: 13px;"
            " padding: 8px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.22); }"
        )
        self.toast.hide()
        self._toast_timer = QTimer(self, singleShot=True, timeout=self.toast.hide)

        # Floating toolbar: owned tool window, always above the canvas, never focused
        self.toolbar = FloatingToolbar(parent=self, vertical=self.config.toolbar_vertical)
        self.toolbar.current_screen_index = self.screen_index
        self.toolbar.current_color = self.config.default_color
        self.toolbar.current_width = float(self.config.default_width)
        self.toolbar._update_style_button()
        self.toolbar.set_active_tool(ToolType.PEN)
        if self.config.toolbar_collapsed:
            self.toolbar.toggle_collapse()
        self.toolbar.move(self.config.toolbar_position[0], self.config.toolbar_position[1])
        self.toolbar.layout_changed.connect(self._fit_toolbar)
        self.canvas.overlay_widgets.append(self.toolbar)

        self._position_on_screen()
        self._connect_signals()
        self._setup_shortcuts()
        self._watch_display_changes()

        # Keep both windows on top of fullscreen browsers / slide shows
        self._topmost_timer = QTimer(self, interval=1000, timeout=self._keep_on_top)

        self.autosave = AutosaveManager(get_strokes_callback=lambda: self.canvas.strokes, parent=self)
        self.autosave.configure(self.config.enable_autosave, self.config.autosave_interval_minutes)

    # ------------------------------------------------------------ geometry
    def _target_screen(self):
        screens = QGuiApplication.screens()
        return screens[self.screen_index] if 0 <= self.screen_index < len(screens) else QGuiApplication.primaryScreen()

    def _watch_display_changes(self):
        app = QGuiApplication.instance()
        if app is not None:
            app.screenAdded.connect(lambda _: self._on_screens_changed())
            app.screenRemoved.connect(lambda _: self._on_screens_changed())
        for scr in QGuiApplication.screens():
            self._connect_screen_signals(scr)

    def _connect_screen_signals(self, scr):
        if scr and scr not in self._connected_screens:
            self._connected_screens.add(scr)
            scr.geometryChanged.connect(lambda _: self.apply_fullscreen_geometry())
            scr.logicalDotsPerInchChanged.connect(lambda _: self.apply_fullscreen_geometry())

    def _on_screens_changed(self):
        screens = QGuiApplication.screens()
        for scr in screens:
            self._connect_screen_signals(scr)
        if self.screen_index >= len(screens):
            self.screen_index = max(0, len(screens) - 1)
        self.toolbar.current_screen_index = self.screen_index
        self.apply_fullscreen_geometry()
        self._fit_toolbar()

    def _fit_toolbar(self):
        screen = self._target_screen()
        if screen and hasattr(self, "toolbar"):
            self.toolbar.fit_to_screen(screen.availableGeometry())

    def _keep_on_top(self):
        if self.isVisible():
            _make_topmost(self)
            _make_topmost(self.toolbar)  # toolbar last => above the canvas

    def _position_on_screen(self):
        screen = self._target_screen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
            self.resize(geo.size())
            self.canvas.setGeometry(0, 0, geo.width(), geo.height())

    def apply_fullscreen_geometry(self):
        """
        Makes the whiteboard canvas fill 100% of the target display viewport.
        Correctly handles High-DPI scaling (e.g. 125%, 150%, 200% Windows scale)
        so Win32 SetWindowPos never shrinks the Qt logical geometry.
        """
        screen = self._target_screen()
        if not screen:
            return
        geo = screen.geometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        self.setGeometry(x, y, w, h)
        self.resize(w, h)
        self.canvas.setGeometry(0, 0, w, h)
        self.canvas.resize(w, h)
        if IS_WIN:
            try:
                # Let Qt manage the DPI-scaled physical geometry; use SWP_NOMOVE | SWP_NOSIZE
                # so Win32 only promotes z-order & frame without shrinking on High-DPI screens!
                user32.SetWindowPos(
                    wintypes.HWND(int(self.winId())),
                    wintypes.HWND(HWND_TOPMOST),
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_FRAMECHANGED | SWP_NOACTIVATE,
                )
            except Exception as e:
                print(f"SetWindowPos error: {e}")
        _make_topmost(self.toolbar)

    def showEvent(self, event):
        super().showEvent(event)
        _set_ex_style(self, add=WS_EX_NOACTIVATE if IS_WIN else 0)
        self.apply_fullscreen_geometry()
        self.toolbar.show()
        _set_ex_style(self.toolbar, add=WS_EX_NOACTIVATE if IS_WIN else 0)
        _set_exclude_from_capture(self.toolbar, True)
        self._fit_toolbar()
        self._update_hotkeys()
        self._topmost_timer.start()
        QTimer.singleShot(50, self.apply_fullscreen_geometry)
        QTimer.singleShot(250, self.apply_fullscreen_geometry)
        QTimer.singleShot(300, self._fit_toolbar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.canvas.resize(self.size())

    def select_screen(self, target_index: int):
        screens = QGuiApplication.screens()
        if not (0 <= target_index < len(screens)):
            return
        scr = screens[target_index]
        geo = scr.geometry()
        dpr = scr.devicePixelRatio()
        phys_w, phys_h = int(round(geo.width() * dpr)), int(round(geo.height() * dpr))
        if target_index == self.screen_index:
            self.apply_fullscreen_geometry()
            self._fit_toolbar()
            if len(screens) == 1:
                self.show_toast(
                    f"Display 1 ({phys_w}×{phys_h} px @ {int(round(dpr * 100))}% scale) is active — "
                    f"Windows reports 1 connected monitor",
                    3200,
                )
            else:
                self.show_toast(f"Display {target_index + 1} ({phys_w}×{phys_h} px) is active", 2200)
            return

        old = self._target_screen().availableGeometry()
        rel = self.toolbar.pos() - old.topLeft()
        self.screen_index = target_index
        self.toolbar.current_screen_index = self.screen_index
        self.config.selected_display = self.screen_index
        self.apply_fullscreen_geometry()
        new = self._target_screen().availableGeometry()
        self.toolbar.move(new.topLeft() + rel)
        self._fit_toolbar()
        self.show_toast(f"Moved whiteboard to Display {self.screen_index + 1} ({phys_w}×{phys_h} px)")

    def move_to_next_screen(self):
        screens = QGuiApplication.screens()
        if len(screens) < 2:
            self.select_screen(0)
            return
        self.select_screen((self.screen_index + 1) % len(screens))

    # ------------------------------------------------------------- signals
    def _connect_signals(self):
        tb = self.toolbar
        tb.tool_changed.connect(self._on_tool_changed)
        tb.color_changed.connect(self.canvas.set_colour)
        tb.width_changed.connect(self.canvas.set_width)
        tb.eraser_radius_changed.connect(self.canvas.set_eraser_radius)
        tb.bg_mode_changed.connect(self._on_bg_mode_changed)
        tb.undo_requested.connect(self.canvas.undo)
        tb.redo_requested.connect(self.canvas.redo)
        tb.clear_requested.connect(self.confirm_and_clear)
        tb.save_annotation_requested.connect(self.save_as_dialog)
        tb.save_screenshot_requested.connect(self.save_as_dialog)
        tb.quick_save_requested.connect(self.quick_save)
        tb.export_transparent_requested.connect(self.export_transparent_dialog)
        tb.save_project_requested.connect(self.save_project_dialog)
        tb.open_project_requested.connect(self.open_project_dialog)
        tb.next_screen_requested.connect(self.move_to_next_screen)
        tb.screen_index_requested.connect(self.select_screen)
        tb.refit_fullscreen_requested.connect(self._refit_fullscreen)
        tb.exit_requested.connect(self.request_exit)

        self.canvas.history_changed.connect(tb.set_history_state)
        self.canvas.stroke_finished.connect(self._on_canvas_modified)
        self.canvas.canvas_cleared.connect(self._on_canvas_modified)

    def _on_canvas_modified(self):
        self.has_unsaved_changes = len(self.canvas.strokes) > 0

    def _on_bg_mode_changed(self, mode: str):
        self.canvas.set_bg_mode(mode)
        names = {
            "desktop": "Transparent Desktop Overlay",
            "white": "Whiteboard Mode (Solid White)",
            "dark": "Blackboard Mode (Solid Dark)",
            "slides": "Slate Board Mode (Dark Navy)",
        }
        self.show_toast(f"Board Mode: {names.get(mode, mode)}  (drawings preserved)", 1800)

    def _refit_fullscreen(self):
        self.apply_fullscreen_geometry()
        self._fit_toolbar()
        geo = self.canvas.size()
        self.show_toast(f"Full-screen canvas fitted to display ({geo.width()}×{geo.height()})", 1800)

    def confirm_and_clear(self):
        """Requests confirmation before deleting all whiteboard content."""
        if not self.canvas.strokes:
            self.show_toast("Whiteboard is already clear", 1500)
            return
        box = QMessageBox(None)
        box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Clear Whiteboard")
        box.setText("Clear all drawings from the whiteboard?")
        box.setInformativeText("You can still press Ctrl+Z (Undo) immediately afterwards if needed.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.canvas.clear()
            self.show_toast("Whiteboard cleared  (Ctrl+Z to undo)", 2000)
        self._keep_on_top()

    def _setup_shortcuts(self):
        if IS_WIN:
            return
        def sc(keys, slot):
            QShortcut(QKeySequence(keys), self, activated=slot,
                      context=Qt.ShortcutContext.ApplicationShortcut)
        sc("F2", self.toggle_mouse_mode)
        sc("F11", self._refit_fullscreen)
        sc("Ctrl+Z", self.canvas.undo)
        sc("Ctrl+Y", self.canvas.redo)
        sc("Ctrl+S", self.save_as_dialog)
        sc("Ctrl+Shift+S", self.quick_save)
        sc("Ctrl+O", self.open_project_dialog)
        sc("Delete", self.confirm_and_clear)
        sc("Esc", lambda: self.set_mouse_mode(True))
        sc("Ctrl+Q", self.request_exit)

    # ------------------------------------------------------ global hotkeys
    def _hotkey_table(self):
        always = {
            self.HK_TOGGLE_F2: (MOD_NOREPEAT, VK_F2, self.toggle_mouse_mode),
            self.HK_TOGGLE_CAM: (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_M, self.toggle_mouse_mode),
        }
        draw_only = {
            self.HK_ESC: (MOD_NOREPEAT, VK_ESCAPE, lambda: self.set_mouse_mode(True)),
            self.HK_UNDO: (MOD_CONTROL, VK_Z, self.canvas.undo),
            self.HK_REDO: (MOD_CONTROL, VK_Y, self.canvas.redo),
            self.HK_CLEAR: (MOD_NOREPEAT, VK_DELETE, self.confirm_and_clear),
            self.HK_SAVE: (MOD_CONTROL | MOD_NOREPEAT, VK_S, self.save_as_dialog),
            self.HK_QUICK_SAVE: (MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_S, self.quick_save),
            self.HK_OPEN: (MOD_CONTROL | MOD_NOREPEAT, VK_O, self.open_project_dialog),
            self.HK_REFIT: (MOD_NOREPEAT, VK_F11, self._refit_fullscreen),
            self.HK_QUIT: (MOD_CONTROL | MOD_NOREPEAT, VK_Q, self.request_exit),
        }
        return always, draw_only

    def _update_hotkeys(self):
        """Register always-on hotkeys, plus draw-mode hotkeys only while drawing,
        so Esc / Ctrl+Z / Delete / F11 go back to Chrome in Mouse mode."""
        if not IS_WIN:
            return
        always, draw_only = self._hotkey_table()
        wanted = dict(always)
        if not self.is_mouse_mode:
            wanted.update(draw_only)
        hwnd = wintypes.HWND(int(self.winId()))
        for hk_id in list(self._registered_hotkeys):
            if hk_id not in wanted:
                user32.UnregisterHotKey(hwnd, hk_id)
                self._registered_hotkeys.discard(hk_id)
        for hk_id, (mods, vk, _) in wanted.items():
            if hk_id not in self._registered_hotkeys:
                if user32.RegisterHotKey(hwnd, hk_id, mods, vk):
                    self._registered_hotkeys.add(hk_id)

    def _unregister_all_hotkeys(self):
        if not IS_WIN:
            return
        hwnd = wintypes.HWND(int(self.winId()))
        for hk_id in list(self._registered_hotkeys):
            user32.UnregisterHotKey(hwnd, hk_id)
        self._registered_hotkeys.clear()

    def nativeEvent(self, eventType, message):
        if IS_WIN and eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                always, draw_only = self._hotkey_table()
                entry = always.get(msg.wParam) or draw_only.get(msg.wParam)
                if entry:
                    QTimer.singleShot(0, entry[2])
                    return True, 0
        return super().nativeEvent(eventType, message)

    # -------------------------------------------------------- mouse / draw
    def _on_tool_changed(self, tool: ToolType):
        if tool == ToolType.MOUSE:
            self.set_mouse_mode(True)
        else:
            if self.is_mouse_mode:
                self.set_mouse_mode(False)
            self.canvas.set_tool(tool)

    def set_mouse_mode(self, enable: bool):
        """Mouse mode: canvas becomes click-through so Chrome / slides receive
        all clicks and scrolls; annotations stay visible. Draw mode: canvas
        captures pen / mouse input."""
        if enable and self.canvas.current_tool != ToolType.MOUSE:
            self._last_draw_tool = self.canvas.current_tool
        self.is_mouse_mode = enable
        try:
            if enable:
                _set_ex_style(self, add=WS_EX_TRANSPARENT | WS_EX_LAYERED)
            else:
                _set_ex_style(self, remove=WS_EX_TRANSPARENT)
        except Exception as e:
            print(f"Click-through style error: {e}")

        self.canvas.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, enable)
        if enable:
            self.canvas.set_tool(ToolType.MOUSE)
            self.toolbar.set_active_tool(ToolType.MOUSE)
        elif self.canvas.current_tool == ToolType.MOUSE:
            last = getattr(self, "_last_draw_tool", ToolType.PEN)
            self.canvas.set_tool(last)
            self.toolbar.set_active_tool(last)
        self._update_hotkeys()
        self._keep_on_top()
        self.show_toast("Mouse mode – clicks go to the presentation  (F2 to draw)" if enable
                        else "Draw mode  (F2 / Esc for mouse)", 1400)

    def toggle_mouse_mode(self):
        self.set_mouse_mode(not self.is_mouse_mode)

    # --------------------------------------------------------------- toast
    def show_toast(self, text: str, ms: int = 2500):
        self.toast.setText(text)
        self.toast.adjustSize()
        x = (self.canvas.width() - self.toast.width()) // 2
        y = self.canvas.height() - self.toast.height() - 60
        self.toast.move(max(0, x), max(0, y))
        self.toast.show()
        self.toast.raise_()
        self._toast_timer.start(ms)

    # --------------------------------------------------------------- saving
    def _default_save_dir(self) -> str:
        folder = getattr(self.config, "save_folder", "") or os.path.join(
            os.path.expanduser("~"), "Pictures", "TransparentWhiteboard")
        os.makedirs(folder, exist_ok=True)
        return folder

    def _capture_clean_background(self):
        """
        Captures the underlying background before any file dialog is opened, ensuring:
          1. Solid board backgrounds ('white', 'dark', 'slides', or custom hex) and custom
             canvas background_pixmap images are preserved directly.
          2. In 'desktop' mode, the live screen beneath the whiteboard is captured without
             the toolbar, popups, toast, cursor, or whiteboard overlay, and without modifying
             the live visible whiteboard (via WDA_EXCLUDEFROMCAPTURE on Windows 10/11).
        """
        if self.canvas.background_pixmap is not None and not self.canvas.background_pixmap.isNull():
            return self.canvas.background_pixmap
        if self.canvas.bg_mode != "desktop":
            return None

        self.toast.hide()
        for attr in ("style_popup", "save_popup", "display_popup", "help_popup"):
            popup = getattr(self.toolbar, attr, None)
            if popup is not None and popup.isVisible():
                popup.hide()

        _set_exclude_from_capture(self.toolbar, True)
        excluded_ok = _set_exclude_from_capture(self, True)
        if excluded_ok:
            QApplication.processEvents()
            captured = ScreenshotCapture.grab_screen_background(self.screen_index)
            _set_exclude_from_capture(self, False)
            return captured

        # Fallback for environments where WDA_EXCLUDEFROMCAPTURE is unsupported
        was_visible = self.isVisible()
        tb_visible = self.toolbar.isVisible()
        try:
            self.toolbar.hide()
            self.hide()
            QApplication.processEvents()
            return ScreenshotCapture.grab_screen_background(self.screen_index)
        finally:
            if was_visible:
                self.show()
            if tb_visible:
                self.toolbar.show()
            if self.is_mouse_mode:
                _set_ex_style(self, add=WS_EX_TRANSPARENT | WS_EX_LAYERED)
            self._keep_on_top()

    def _run_file_dialog(self, dialog_fn):
        """
        Switches control to Mouse mode and temporarily suspends topmost enforcement and
        global hotkeys while a native file dialog is open so the user has full normal
        mouse and keyboard input to type filenames and click dialog controls.
        """
        if not self.is_mouse_mode:
            self.set_mouse_mode(True)
        self._topmost_timer.stop()
        self._unregister_all_hotkeys()
        if IS_WIN:
            for w in (self, self.toolbar):
                if w is not None and w.isVisible():
                    user32.SetWindowPos(
                        wintypes.HWND(int(w.winId())),
                        wintypes.HWND(HWND_NOTOPMOST),
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                    )
        try:
            return dialog_fn()
        finally:
            self._update_hotkeys()
            self._keep_on_top()
            self._topmost_timer.start()

    def quick_save(self):
        """Instant save of screen/board + strokes to ~/Pictures/TransparentWhiteboard."""
        if not self.is_mouse_mode:
            self.set_mouse_mode(True)
        name = time.strftime("whiteboard_%Y%m%d_%H%M%S.png")
        bg_pixmap = self._capture_clean_background()
        self._capture_to(os.path.join(self._default_save_dir(), name), bg_pixmap=bg_pixmap)

    def save_as_dialog(self):
        """Captures the clean background first, switches to Mouse mode, prompts for destination file path, then saves."""
        bg_pixmap = self._capture_clean_background()
        default_name = time.strftime("whiteboard_%Y%m%d_%H%M%S.png")
        file_path, _ = self._run_file_dialog(
            lambda: QFileDialog.getSaveFileName(
                None,
                "Save Whiteboard as PNG (Background + Annotations)",
                os.path.join(self._default_save_dir(), default_name),
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
            )
        )
        if file_path:
            self._capture_to(file_path, bg_pixmap=bg_pixmap)

    # Backwards-compatible alias
    save_screen_with_strokes_dialog = save_as_dialog

    def export_transparent_dialog(self):
        """Exports only the drawn annotations on a transparent PNG background."""
        default_name = time.strftime("whiteboard_annotations_%Y%m%d_%H%M%S.png")
        file_path, _ = self._run_file_dialog(
            lambda: QFileDialog.getSaveFileName(
                None,
                "Export Transparent Annotations (PNG)",
                os.path.join(self._default_save_dir(), default_name),
                "PNG Image (*.png)",
            )
        )
        if not file_path:
            return
        geo = self.canvas.size()
        ok = ImageExporter.export_annotations_to_file(
            file_path=file_path,
            strokes=self.canvas.strokes,
            width=max(1, geo.width()),
            height=max(1, geo.height()),
            format_name="PNG",
            transparent=True,
        )
        verified = ok and os.path.exists(file_path) and os.path.getsize(file_path) > 0
        if verified:
            self.has_unsaved_changes = False
            self.show_toast(f"Saved transparent PNG: {file_path}", 3500)
        else:
            self.show_toast(f"Error: could not save {file_path}", 3500)

    def save_project_dialog(self):
        """Saves editable strokes, colours, highlighters, lines, and arrows to a .whiteboard file."""
        default_name = time.strftime("lecture_%Y%m%d_%H%M%S.whiteboard")
        file_path, _ = self._run_file_dialog(
            lambda: QFileDialog.getSaveFileName(
                None,
                "Save Editable Whiteboard Project",
                os.path.join(self._default_save_dir(), default_name),
                "Whiteboard Project (*.whiteboard);;JSON Files (*.json)",
            )
        )
        if not file_path:
            return
        geo = self.canvas.size()
        ok = ProjectPersistence.save_project(
            file_path=file_path,
            strokes=self.canvas.strokes,
            width=max(1, geo.width()),
            height=max(1, geo.height()),
            display_index=self.screen_index,
        )
        verified = ok and os.path.exists(file_path) and os.path.getsize(file_path) > 0
        if verified:
            self.has_unsaved_changes = False
            self.show_toast(f"Saved editable project: {file_path}", 3500)
        else:
            self.show_toast(f"Error: could not save project {file_path}", 3500)

    def open_project_dialog(self):
        """Opens a previously saved .whiteboard project file and restores its strokes."""
        file_path, _ = self._run_file_dialog(
            lambda: QFileDialog.getOpenFileName(
                None,
                "Open Editable Whiteboard Project",
                self._default_save_dir(),
                "Whiteboard Project (*.whiteboard *.json);;All Files (*)",
            )
        )
        if not file_path:
            return
        data = ProjectPersistence.load_project(file_path)
        if data is not None and "strokes" in data:
            self.canvas.load_strokes(data["strokes"])
            self.has_unsaved_changes = False
            self.show_toast(f"Loaded {len(data['strokes'])} stroke(s) from {os.path.basename(file_path)}", 3000)
        else:
            self.show_toast(f"Error: invalid or unreadable project file ({os.path.basename(file_path)})", 3500)

    def _capture_to(self, file_path: str, bg_pixmap=None):
        if bg_pixmap is None and self.canvas.bg_mode == "desktop":
            bg_pixmap = self._capture_clean_background()
        self._perform_capture(file_path, bg_pixmap=bg_pixmap)

    def _perform_capture(self, file_path: str, bg_pixmap=None):
        success = False
        try:
            fmt = "JPEG" if file_path.lower().endswith((".jpg", ".jpeg")) else "PNG"
            scr = self._target_screen()
            dpr = scr.devicePixelRatio() if scr is not None else 1.0
            geo = self.canvas.size()
            success = ScreenshotCapture.capture_screen_with_annotations(
                file_path=file_path,
                strokes=self.canvas.strokes,
                screen_index=self.screen_index,
                format_name=fmt,
                bg_mode=self.canvas.bg_mode,
                background_pixmap=bg_pixmap if bg_pixmap is not None else self.canvas.background_pixmap,
                width=max(1, geo.width()),
                height=max(1, geo.height()),
                dpr=dpr,
            )
        finally:
            if self.is_mouse_mode:
                _set_ex_style(self, add=WS_EX_TRANSPARENT | WS_EX_LAYERED)
            self._keep_on_top()
        verified = success and os.path.exists(file_path) and os.path.getsize(file_path) > 0
        if verified:
            self.has_unsaved_changes = False
            self.show_toast(f"Saved PNG (background + strokes): {file_path}", 3500)
        else:
            self.show_toast(f"Save failed: could not write {file_path}", 3500)

    # ---------------------------------------------------------------- close
    def request_exit(self):
        """Prompts if there are unsaved strokes on the canvas before quitting."""
        if self.has_unsaved_changes and self.canvas.strokes:
            box = QMessageBox(None)
            box.setWindowFlags(box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Unsaved Whiteboard Drawings")
            box.setText("You have unsaved drawings on the whiteboard.")
            box.setInformativeText("Do you want to save your whiteboard before exiting?")
            box.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            box.setDefaultButton(QMessageBox.StandardButton.Save)
            choice = box.exec()
            if choice == QMessageBox.StandardButton.Cancel:
                self._keep_on_top()
                return
            if choice == QMessageBox.StandardButton.Save:
                self.save_as_dialog()
                if self.has_unsaved_changes:
                    return
        self.has_unsaved_changes = False
        self.close()

    def closeEvent(self, event):
        if self.prompt_unsaved_on_close and self.has_unsaved_changes and self.canvas.strokes:
            self.request_exit()
            if self.has_unsaved_changes:
                event.ignore()
                return
        self._topmost_timer.stop()
        self._unregister_all_hotkeys()
        pos = self.toolbar.pos()
        self.config.toolbar_position = [pos.x(), pos.y()]
        self.config.toolbar_vertical = self.toolbar.is_vertical
        self.config.toolbar_collapsed = self.toolbar.is_collapsed
        ConfigManager.save(self.config)
        self.toolbar.close()
        super().closeEvent(event)
