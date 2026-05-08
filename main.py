import os
import sys
from PySide6.QtWidgets import QApplication, QDialog
import qdarktheme

from core.app_controller import AppController
from ui.main_window import MainWindow
from ui.team_selection_dialog import TeamSelectionDialog
from models.config_manager import ConfigManager

if __name__ == "__main__":
    # Ensure necessary folders exist
    os.makedirs("database/categories", exist_ok=True)
    os.makedirs("database/assets", exist_ok=True)
    os.makedirs("database/templates", exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # Check for first-run onboarding
    if not os.path.exists("settings.json"):
        onboarding = TeamSelectionDialog()
        # Use dark theme for onboarding too
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        if onboarding.exec() != QDialog.Accepted:
            sys.exit(0)
    
    # Apply dark theme
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))

    
    # Initialize Core Logic
    controller = AppController()
    
    # Initialize Main Window
    window = MainWindow(controller)
    window.show()
    
    sys.exit(app.exec())
