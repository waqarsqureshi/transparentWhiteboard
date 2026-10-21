import os
import tempfile
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor, QPainter
from canvas.stroke import Stroke
from export.screenshot import ScreenshotCapture
from export.image_export import ImageExporter
from ui.main_window import TransparentWhiteboardWindow
from app.constants import ToolType


def _app():
    return QApplication.instance() or QApplication([])


def test_screenshot_capture_methods():
    _app()
    stroke = Stroke(id="s1", tool="pen", colour="#FF3B30", width=6.0)
    stroke.add_point(10, 10)
    stroke.add_point(50, 50)

    pixmap = ScreenshotCapture.capture_desktop_with_annotations([stroke], screen_index=0)
    assert pixmap is not None
    assert not pixmap.isNull()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        success = ScreenshotCapture.capture_screen_with_annotations(tmp_path, [stroke], screen_index=0)
        assert success is True
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_png_export_preserves_white_coloured_and_image_backgrounds_with_strokes():
    _app()
    pen_stroke = Stroke(id="pen-1", tool="pen", colour="#FF0000", width=8.0)
    pen_stroke.add_point(50, 50)
    pen_stroke.add_point(150, 50)

    highlighter = Stroke(id="hl-1", tool="highlighter", colour="#FFCC00", width=24.0)
    highlighter.add_point(50, 120)
    highlighter.add_point(150, 120)

    arrow = Stroke(id="arr-1", tool="arrow", colour="#007AFF", width=6.0)
    arrow.add_point(50, 180)
    arrow.add_point(150, 180)

    line = Stroke(id="ln-1", tool="line", colour="#34C759", width=6.0)
    line.add_point(50, 230)
    line.add_point(150, 230)

    strokes = [pen_stroke, highlighter, arrow, line]

    # 1. Plain white background + strokes
    pm_white = ScreenshotCapture.capture_desktop_with_annotations(
        strokes, bg_mode="white", width=300, height=300, dpr=1.0
    )
    img_white = pm_white.toImage()
    # Unannotated corner is white (#FCFCFC = 252, 252, 252)
    bg_px = img_white.pixelColor(10, 10)
    assert (bg_px.red(), bg_px.green(), bg_px.blue(), bg_px.alpha()) == (252, 252, 252, 255)
    # Pen stroke at (100, 50) is pure red
    pen_px = img_white.pixelColor(100, 50)
    assert pen_px.red() > 240 and pen_px.green() < 20 and pen_px.blue() < 20
    # Translucent yellow highlighter at (100, 120) blends yellow with white background
    hl_px = img_white.pixelColor(100, 120)
    assert hl_px.red() > 245 and 200 < hl_px.green() < 245 and 120 < hl_px.blue() < 200
    # Arrow shaft at (90, 180) and Line at (100, 230) are rendered at their exact positions
    arr_px = img_white.pixelColor(90, 180)
    assert arr_px.blue() > 200 and arr_px.red() < 30
    ln_px = img_white.pixelColor(100, 230)
    assert ln_px.green() > 170 and ln_px.red() < 80

    # 2. Coloured ('slides' navy #0F172A) background + translucent highlighter blends with dark bg
    pm_dark = ScreenshotCapture.capture_desktop_with_annotations(
        strokes, bg_mode="slides", width=300, height=300, dpr=1.0
    )
    img_dark = pm_dark.toImage()
    dark_bg = img_dark.pixelColor(10, 10)
    assert (dark_bg.red(), dark_bg.green(), dark_bg.blue()) == (15, 23, 42)
    # Highlighter over dark background is visibly darker than over white background (background shows through)
    hl_dark_px = img_dark.pixelColor(100, 120)
    assert hl_dark_px.blue() < hl_px.blue()
    assert hl_dark_px.red() > dark_bg.red()

    # 3. Image background (e.g. slide/document pixmap) + strokes composited on top
    bg_pixmap = QPixmap(300, 300)
    bg_pixmap.fill(QColor(30, 144, 255))  # DodgerBlue image background
    p = QPainter(bg_pixmap)
    p.fillRect(0, 100, 300, 40, QColor(255, 255, 255))  # White banner under highlighter at y=120
    p.end()

    pm_img = ScreenshotCapture.capture_desktop_with_annotations(
        strokes, bg_mode="desktop", background_pixmap=bg_pixmap, width=300, height=300, dpr=1.0
    )
    img_comp = pm_img.toImage()
    assert (img_comp.pixelColor(10, 10).red(), img_comp.pixelColor(10, 10).green(), img_comp.pixelColor(10, 10).blue()) == (30, 144, 255)
    assert img_comp.pixelColor(100, 50).red() > 240  # Red pen stroke over blue image


def test_live_whiteboard_unchanged_and_no_ui_elements_in_exported_png():
    _app()
    win = TransparentWhiteboardWindow(screen_index=0)
    win.show()
    win.canvas.set_bg_mode("white")
    win.canvas._handle_pointer_down(100.0, 100.0, 1.0)
    win.canvas._handle_pointer_move(200.0, 100.0, 1.0)
    win.canvas._handle_pointer_up()

    # Activate laser pointer and position toolbar over (40, 40) to verify neither is drawn into exported PNG
    win.canvas.set_tool(ToolType.LASER)
    win.canvas._handle_pointer_move(150.0, 150.0, 1.0)
    win.toolbar.move(20, 20)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        win._capture_to(tmp_path)
        assert os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0
        exported = QPixmap(tmp_path).toImage()
        # Laser pointer at (150, 150) and toolbar at (30, 30) must NOT appear in exported image
        dpr = exported.devicePixelRatio() or (exported.width() / max(1, win.canvas.width()))
        lx, ly = int(150 * dpr), int(150 * dpr)
        tx, ty = int(30 * dpr), int(30 * dpr)
        assert exported.pixelColor(lx, ly).red() == 252 and exported.pixelColor(lx, ly).green() == 252
        assert exported.pixelColor(tx, ty).red() == 252 and exported.pixelColor(tx, ty).green() == 252
        # Live whiteboard state is completely unchanged after export
        assert len(win.canvas.strokes) == 1
        assert win.canvas.bg_mode == "white"
        assert win.isVisible()
    finally:
        win.toolbar.close()
        win.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
