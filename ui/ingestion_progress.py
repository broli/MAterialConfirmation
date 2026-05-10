from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

class IngestionProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Ingestion Progress")
        self.resize(600, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas, monospace;")
        layout.addWidget(self.log_view)
        
        footer = QHBoxLayout()
        
        self.btn_abort = QPushButton("🛑 Abort Process")
        self.btn_abort.setStyleSheet("background-color: #d32f2f; color: white;")
        self.btn_abort.clicked.connect(self.reject)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        
        footer.addStretch()
        footer.addWidget(self.btn_abort)
        footer.addWidget(self.btn_close)
        layout.addLayout(footer)

    def append_log(self, message: str):
        self.log_view.append(message)
        # Auto scroll to bottom
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        
        # Also update the top label for the most recent high-level status
        if "AI Matching" in message or "Extracting" in message or "Checking" in message or "Match" in message:
            self.status_label.setText(message)

    def set_finished(self):
        self.btn_close.setEnabled(True)
        self.btn_abort.hide()
        self.status_label.setText("✅ Ingestion Complete!")
