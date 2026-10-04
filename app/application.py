import sys
import logging
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from app.config import ConfigManager

def setup_logging():
    log_dir = ConfigManager.get_config_dir()
    log_file = os.path.join(log_dir, "whiteboard.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Transparent Whiteboard starting up.")

class WhiteboardApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        setup_logging()
        sys.excepthook = self.handle_unhandled_exception

    def handle_unhandled_exception(self, exc_type, exc_value, exc_traceback):
        logging.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Whiteboard Error")
        msg.setText("An unexpected problem occurred.")
        msg.setInformativeText(f"{exc_value}")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
