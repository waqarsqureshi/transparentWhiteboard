from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QPoint
from app.constants import ToolType, BackgroundMode
from canvas.canvas import TransparentCanvas
from ui.toolbar import FloatingToolbar


def _app():
    return QApplication.instance() or QApplication([])


def test_canvas_tool_switching_and_mouse_mode():
    _app()
    canvas = TransparentCanvas()
    assert canvas.current_tool == ToolType.PEN
    canvas.set_tool(ToolType.ARROW)
    assert canvas.current_tool == ToolType.ARROW
    canvas.set_tool(ToolType.RECTANGLE)
    assert canvas.current_tool == ToolType.RECTANGLE
    canvas.set_tool(ToolType.MOUSE)
    assert canvas.current_tool == ToolType.MOUSE
    canvas.set_bg_mode(BackgroundMode.WHITE.value)
    assert canvas.bg_mode == "white"
    canvas.set_bg_mode(BackgroundMode.DESKTOP.value)
    assert canvas.bg_mode == "desktop"


def test_toolbar_mode_selection():
    _app()
    toolbar = FloatingToolbar()
    received = []
    toolbar.tool_changed.connect(received.append)

    toolbar.btn_mouse.click()
    assert ToolType.MOUSE in received
    assert toolbar.btn_mouse.property("mouseActive") is True

    toolbar.btn_pen.click()
    assert ToolType.PEN in received
    assert toolbar.btn_pen.property("active") is True

    # Programmatic sync must not re-emit (prevents F2 toggle recursion)
    received.clear()
    toolbar.set_active_tool(ToolType.MOUSE)
    assert received == []
    assert toolbar.btn_mouse.property("mouseActive") is True

    assert not toolbar.is_collapsed
    toolbar.toggle_collapse()
    assert toolbar.is_collapsed
    toolbar.toggle_collapse()
    assert not toolbar.is_collapsed

    # Help '?' button opens HelpPopup with instructions and shortcuts
    assert hasattr(toolbar, "btn_help")
    toolbar.btn_help.click()
    assert hasattr(toolbar, "help_popup")
    assert toolbar.help_popup.isVisible()
    toolbar.help_popup.hide()
    toolbar.close()


def test_toolbar_is_compact_and_fits_screen():
    _app()
    toolbar = FloatingToolbar()
    toolbar.show()
    # Compact: horizontal bar well under a typical laptop width
    assert toolbar.width() < 800, toolbar.width()

    # Vertical orientation is narrow
    toolbar.toggle_orientation()
    assert toolbar.is_vertical
    assert toolbar.width() < 80

    # Back to horizontal, then fit into a very narrow screen -> auto vertical / collapsed
    toolbar.toggle_orientation()
    small = QRect(0, 0, 400, 300)
    toolbar.move(1000, 1000)
    toolbar.fit_to_screen(small)
    assert toolbar.is_vertical
    assert small.contains(toolbar.frameGeometry())
    toolbar.close()


def test_canvas_ignores_presses_over_toolbar():
    _app()
    canvas = TransparentCanvas()
    toolbar = FloatingToolbar()
    toolbar.show()
    canvas.overlay_widgets.append(toolbar)
    inside = toolbar.frameGeometry().center()
    outside = toolbar.frameGeometry().bottomRight() + QPoint(50, 50)
    assert canvas._is_over_overlay(inside)
    assert not canvas._is_over_overlay(outside)
    toolbar.hide()
    assert not canvas._is_over_overlay(inside)
    toolbar.close()


def test_only_laser_works_without_mouse_press():
    _app()
    canvas = TransparentCanvas()
    # Default tool is PEN
    assert canvas.current_tool == ToolType.PEN

    # Moving without pressing does NOT create a pen stroke
    canvas._handle_pointer_move(50.0, 50.0, 1.0)
    canvas._handle_pointer_move(100.0, 100.0, 1.0)
    assert canvas.current_stroke is None
    assert len(canvas.strokes) == 0

    # Pressing, dragging, and releasing DOES create a pen stroke
    canvas._handle_pointer_down(10.0, 20.0, 1.0)
    canvas._handle_pointer_move(60.0, 20.0, 1.0)
    canvas._handle_pointer_move(120.0, 20.0, 1.0)
    canvas._handle_pointer_up()
    assert len(canvas.strokes) == 1

    # Switching to ERASER and moving WITHOUT pressing does NOT erase the stroke
    canvas.set_tool(ToolType.ERASER)
    canvas._handle_pointer_move(60.0, 20.0, 1.0)
    assert len(canvas.strokes) == 1
    assert len(canvas.strokes[0].points) == 3

    # Pressing and rubbing with ERASER partially erases the stroke and records 1 undo step
    canvas._handle_pointer_down(60.0, 20.0, 1.0)
    canvas._handle_pointer_move(65.0, 20.0, 1.0)
    canvas._handle_pointer_up()
    assert len(canvas.strokes) == 2
    canvas.undo()
    assert len(canvas.strokes) == 1

    # Switching to LASER updates laser position and trail WITHOUT pressing mouse button
    canvas.set_tool(ToolType.LASER)
    assert not canvas._pointer_pressed
    canvas._handle_pointer_move(200.0, 150.0, 1.0)
    canvas._handle_pointer_move(220.0, 160.0, 1.0)
    assert canvas.laser_pos is not None
    assert len(canvas.laser_trail) >= 2
    # Laser does not modify strokes
    assert len(canvas.strokes) == 1

    # Selecting another tool immediately clears laser pointer and trail
    canvas.set_tool(ToolType.HIGHLIGHTER)
    assert canvas.laser_pos is None
    assert len(canvas.laser_trail) == 0


def test_fullscreen_geometry_and_toolbar_popups():
    _app()
    from ui.main_window import TransparentWhiteboardWindow
    win = TransparentWhiteboardWindow(screen_index=0)
    win.show()
    win.apply_fullscreen_geometry()
    scr_geo = win._target_screen().geometry()
    assert win.geometry().width() == scr_geo.width()
    assert win.geometry().height() == scr_geo.height()
    assert win.canvas.width() == scr_geo.width()
    assert win.canvas.height() == scr_geo.height()

    # Undo/Redo disabled initially when history is empty
    assert not win.toolbar.btn_undo.isEnabled()
    assert not win.toolbar.btn_redo.isEnabled()

    # Drawing enables Undo
    win.canvas._handle_pointer_down(20.0, 20.0, 1.0)
    win.canvas._handle_pointer_move(80.0, 80.0, 1.0)
    win.canvas._handle_pointer_up()
    assert win.toolbar.btn_undo.isEnabled()
    assert win.has_unsaved_changes is True

    # Clicking the Save button automatically switches control to Mouse mode
    assert win.is_mouse_mode is False
    win.toolbar.btn_save.click()
    assert win.is_mouse_mode is True
    assert win.canvas.current_tool == ToolType.MOUSE
    win.toolbar.save_popup.hide()

    win.toolbar.close()
    win.close()
