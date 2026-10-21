from PySide6.QtGui import QGuiApplication, QPainter, QPixmap, QImage, QColor
from PySide6.QtCore import QRectF, QSize
from typing import List, Optional
from canvas.stroke import Stroke
from canvas.renderer import StrokeRenderer


BOARD_BG_COLOURS = {
    "white": QColor(252, 252, 252),
    "dark": QColor(24, 24, 27),
    "slides": QColor(15, 23, 42),
}


class ScreenshotCapture:
    @staticmethod
    def _is_capture_restricted_or_blank(pixmap: Optional[QPixmap]) -> bool:
        """
        Detects when OS/sandbox screen capture is unavailable or blocked by permissions
        (which on Windows GDI causes grabWindow(0) to return a null pixmap or an
        uninitialized all-zero black buffer).
        """
        if pixmap is None or pixmap.isNull():
            return True
        img = pixmap.toImage()
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return True
        # Sample a grid of points across the screen; if every sampled pixel is pure (0,0,0),
        # GDI BitBlt failed or was blocked by OS capture restrictions.
        xs = [int(w * f) for f in (0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)]
        ys = [int(h * f) for f in (0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95)]
        for y in ys:
            for x in xs:
                c = img.pixelColor(min(x, w - 1), min(y, h - 1))
                if c.red() != 0 or c.green() != 0 or c.blue() != 0:
                    return False
        return True

    @staticmethod
    def grab_screen_background(screen_index: int = 0) -> Optional[QPixmap]:
        """
        Captures the target display's live screen content.
        Note: QScreen.grabWindow(0, x, y, w, h) interprets (x, y) relative to the target
        screen's top-left corner, so (0, 0, width, height) must be used for multi-monitor setups.
        Returns None if OS screen capture is unavailable or blocked.
        """
        screens = QGuiApplication.screens()
        if not screens:
            return None
        target_screen = screens[screen_index] if 0 <= screen_index < len(screens) else screens[0]
        geo = target_screen.geometry()
        pixmap = target_screen.grabWindow(0, 0, 0, geo.width(), geo.height())
        if ScreenshotCapture._is_capture_restricted_or_blank(pixmap):
            return None
        return pixmap

    @staticmethod
    def capture_desktop_with_annotations(
        strokes: List[Stroke],
        screen_index: int = 0,
        bg_mode: str = "desktop",
        background_pixmap: Optional[QPixmap] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpr: Optional[float] = None,
    ) -> Optional[QPixmap]:
        """
        Creates an offscreen export surface with the display's dimensions and pixel ratio,
        renders the visible background first (captured screen, custom background image, or
        board colour), and composites all whiteboard strokes on top.
        """
        screens = QGuiApplication.screens()
        target_screen = (
            screens[screen_index]
            if screens and 0 <= screen_index < len(screens)
            else (screens[0] if screens else None)
        )

        if target_screen is not None:
            geo = target_screen.geometry()
            logical_w = width if (width and width > 0) else geo.width()
            logical_h = height if (height and height > 0) else geo.height()
            scale = dpr if (dpr and dpr > 0) else target_screen.devicePixelRatio()
        else:
            logical_w = width if (width and width > 0) else 1920
            logical_h = height if (height and height > 0) else 1080
            scale = dpr if (dpr and dpr > 0) else 1.0

        phys_w = max(1, int(round(logical_w * scale)))
        phys_h = max(1, int(round(logical_h * scale)))

        export_image = QImage(QSize(phys_w, phys_h), QImage.Format.Format_ARGB32_Premultiplied)
        export_image.setDevicePixelRatio(scale)

        # 1. Render background layer first
        if bg_mode in BOARD_BG_COLOURS:
            export_image.fill(BOARD_BG_COLOURS[bg_mode])
        elif bg_mode and bg_mode.startswith("#") and QColor(bg_mode).isValid():
            export_image.fill(QColor(bg_mode))
        else:
            # Default solid surface fallback if desktop screen capture is restricted by OS
            export_image.fill(BOARD_BG_COLOURS["white"])

        painter = QPainter(export_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        target_rect = QRectF(0.0, 0.0, float(logical_w), float(logical_h))

        if background_pixmap is not None and not background_pixmap.isNull():
            painter.drawPixmap(target_rect.toRect(), background_pixmap)
        elif bg_mode == "desktop":
            captured = ScreenshotCapture.grab_screen_background(screen_index=screen_index)
            if captured is not None and not captured.isNull():
                painter.drawPixmap(target_rect.toRect(), captured)

        # 2. Composite all whiteboard strokes on top of the background
        StrokeRenderer.render_all(painter, strokes)
        painter.end()

        result = QPixmap.fromImage(export_image)
        result.setDevicePixelRatio(scale)
        return result

    @staticmethod
    def capture_screen_with_annotations(
        file_path: str,
        strokes: List[Stroke],
        screen_index: int = 0,
        format_name: str = "PNG",
        bg_mode: str = "desktop",
        background_pixmap: Optional[QPixmap] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpr: Optional[float] = None,
    ) -> bool:
        """Composites background + annotations onto a single flattened image and saves to file_path."""
        pixmap = ScreenshotCapture.capture_desktop_with_annotations(
            strokes=strokes,
            screen_index=screen_index,
            bg_mode=bg_mode,
            background_pixmap=background_pixmap,
            width=width,
            height=height,
            dpr=dpr,
        )
        if pixmap and not pixmap.isNull():
            return pixmap.save(file_path, format_name)
        return False
