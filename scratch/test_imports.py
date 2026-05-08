import sys
try:
    from PySide6.QtWidgets import QApplication
    print("PySide6 imported successfully")
except ImportError as e:
    print(f"Failed to import PySide6: {e}")

try:
    import qdarktheme
    print("qdarktheme imported successfully")
except ImportError as e:
    print(f"Failed to import qdarktheme: {e}")

print(f"Python version: {sys.version}")
print(f"Executable: {sys.executable}")
