from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QColorDialog
from PySide6.QtGui import QGuiApplication, QColor, QFont
from PySide6.QtCore import Qt
from app.config import WhiteboardConfig, ConfigManager

class LauncherDialog(QDialog):
    def __init__(self, config: WhiteboardConfig = None, parent=None):
        super().__init__(parent)
        self.config = config or ConfigManager.load()
        self.selected_display_index = self.config.selected_display
        self.setWindowTitle("Transparent Whiteboard")
        self.setFixedSize(380, 360)
        self.setStyleSheet("""
            QDialog { background-color: #18181B; color: #F4F4F5; }
            QLabel { color: #E4E4E7; }
            QComboBox { background-color: #27272A; color: #FAFAFA; border: 1px solid #3F3F46; border-radius: 6px; padding: 6px; }
            QPushButton#StartButton { background-color: #2563EB; color: white; font-weight: 600; font-size: 15px; border-radius: 8px; padding: 12px; }
            QPushButton#StartButton:hover { background-color: #1D4ED8; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title_label = QLabel("Transparent Whiteboard")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        sub_label = QLabel("Annotate directly over any Windows desktop application")
        sub_label.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_label)

        layout.addSpacing(10)

        disp_title = QLabel("Select Display:")
        disp_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(disp_title)

        self.display_combo = QComboBox()
        screens = QGuiApplication.screens()
        for idx, screen in enumerate(screens):
            geo = screen.geometry()
            self.display_combo.addItem(f"Display {idx + 1}: {geo.width()}x{geo.height()}", idx)
        if 0 <= self.config.selected_display < len(screens):
            self.display_combo.setCurrentIndex(self.config.selected_display)
        self.display_combo.currentIndexChanged.connect(self._on_display_changed)
        layout.addWidget(self.display_combo)

        self.start_btn = QPushButton("Start Whiteboard", objectName="StartButton")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.accept)
        layout.addWidget(self.start_btn)

    def _on_display_changed(self, index: int):
        self.selected_display_index = self.display_combo.currentData()
        self.config.selected_display = self.selected_display_index
        ConfigManager.save(self.config)

    def get_selected_display(self) -> int:
        return self.selected_display_index
