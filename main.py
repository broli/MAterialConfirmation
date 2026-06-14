import os
import sys

# Force Qt to use the native Linux file dialogs via the XDG portal
if sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORMTHEME"] = "xdgdesktopportal"

# Determine the directory of the script or the compiled executable
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller compiled executable
    app_dir = os.path.dirname(sys.executable)
else:
    # Running from the source script
    app_dir = os.path.dirname(os.path.abspath(__file__))

# Lock the working directory to the app's root folder
os.chdir(app_dir)

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
        if onboarding.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
    
    # Apply dark theme
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))

    
    # Initialize Core Logic
    controller = AppController()
    
    # Initialize Main Window
    window = MainWindow(controller)
    window.show()
    
    sys.exit(app.exec())
