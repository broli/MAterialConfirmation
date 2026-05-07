import os
import sys
from PySide6.QtWidgets import QApplication
import qdarktheme

from core.app_controller import AppController
from ui.main_window import MainWindow

if __name__ == "__main__":
    # Ensure necessary folders exist
    os.makedirs("database/categories", exist_ok=True)
    os.makedirs("database/assets", exist_ok=True)
    os.makedirs("database/templates", exist_ok=True)
    
    
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    # Initialize Core Logic
    controller = AppController()
    
    # Initialize Main Window
    window = MainWindow(controller)
    window.show()
    
    sys.exit(app.exec())
