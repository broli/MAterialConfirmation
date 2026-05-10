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
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        self.model_status_label = QLabel("")
        self.model_status_label.setStyleSheet("color: #4caf50; font-weight: bold; font-style: italic; font-size: 12px;")
        self.model_status_label.hide()
        layout.addWidget(self.model_status_label)
        
        self.countdown_label = QLabel("")
        self.countdown_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.countdown_label.hide()
        layout.addWidget(self.countdown_label)
        
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

    def update_status(self, text: str):
        self.status_label.setText(text)
        
    def update_model_status(self, text: str):
        if text:
            self.model_status_label.setText(f"🤖 {text}")
            self.model_status_label.show()
        else:
            self.model_status_label.hide()
        
    def update_countdown(self, seconds: int):
        if seconds > 0:
            self.countdown_label.setText(f"⏳ Retrying in {seconds}s...")
            self.countdown_label.show()
        else:
            self.countdown_label.hide()

    def set_finished(self):
        self.btn_close.setEnabled(True)
        self.btn_abort.hide()
        self.status_label.setText("✅ Ingestion Complete!")
